import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import torch.nn.functional as F
from chunk_rag import extract_by_html2text_db_nolist, split_text_by_punctuation
import os 
result_dir = './result'


model_name_or_path = 'Qwen/Qwen2-1.5B-Instruct'
device_map = "auto"
tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name_or_path, trust_remote_code=True, device_map=device_map)
model.eval()

# 计算两个句子之间的概率差异
def get_prob_subtract(model, tokenizer, sentence1, sentence2, language):
    # 中文和英文的查询模板
    if language == 'zh':
        query = f'''这是一个文本分块任务。你是一位文本分析专家，请根据提供的句子的逻辑结构和语义内容，
从下面两种方案中选择一种分块方式：
1. 将“{sentence1}{sentence2}”分割成“{sentence1}”与“{sentence2}”两部分；
2. 将“{sentence1}{sentence2}”不进行分割，保持原形式；
请回答1或2。'''
    else:
        query = f'''This is a text chunking task. You are a text analysis expert. Please choose one of the following two options based on the logical structure and semantic content of the provided sentence:
1. Split "{sentence1} {sentence2}" into "{sentence1}" and "{sentence2}" two parts;
2. Keep "{sentence1} {sentence2}" unsplit in its original form;
Please answer 1 or 2.'''
    
    # 构建提示并编码
    prompt = f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"
    prompt_ids = tokenizer.encode(prompt, return_tensors='pt').to(model.device)
    input_ids = prompt_ids
    output_ids = tokenizer.encode(['1', '2'], return_tensors='pt').to(model.device)
    
    with torch.no_grad():
        outputs = model(input_ids)
        next_token_logits = outputs.logits[:, -1, :]
        token_probs = F.softmax(next_token_logits, dim=-1)
    
    next_token_prob_1 = token_probs[:, output_ids[:, 0]].item()
    next_token_prob_2 = token_probs[:, output_ids[:, 1]].item()
    
    # 计算概率差
    prob_subtract = next_token_prob_2 - next_token_prob_1
    return prob_subtract

# 文本分块逻辑
def meta_chunking(original_text, base_model, language, ppl_threshold, chunk_length):
    chunk_length = int(chunk_length)
    final_text = ""

    if base_model == 'PPL Chunking':
        # 调用 PPL Chunking 方法
        final_chunks = extract_by_html2text_db_nolist(original_text, model, tokenizer, ppl_threshold, language=language)
    else:
        #使用Margin Sampling Chunking
        full_segments = split_text_by_punctuation(original_text, language)
        threshold = 0
        threshold_list = []
        final_chunks = []

        tmp = ''
        # 计算前后两个句子的概率并处理
        for sentence in full_segments:
            if tmp == '':
                tmp += sentence
            else:
                prob_subtract = get_prob_subtract(model, tokenizer, tmp, sentence, language)
                threshold_list.append(prob_subtract)
                if prob_subtract > threshold:
                    tmp += ' ' + sentence
                else:
                    final_chunks.append(tmp)
                    tmp = sentence
                # 更新阈值
                if len(threshold_list) >= 5:
                    last_ten = threshold_list[-5:]
                    avg = sum(last_ten) / len(last_ten)
                    threshold = avg
        if tmp != '':
            final_chunks.append(tmp)

    # 动态合并
    merged_paragraphs = []
    current_paragraph = ""
    for paragraph in final_chunks:
        if language == 'zh':
            if len(current_paragraph) + len(paragraph) <= chunk_length:
                current_paragraph += paragraph
            else:
                merged_paragraphs.append(current_paragraph)
                current_paragraph = paragraph
        else:
            if len(current_paragraph.split()) + len(paragraph.split()) <= chunk_length:
                current_paragraph += ' ' + paragraph
            else:
                merged_paragraphs.append(current_paragraph)
                current_paragraph = paragraph
    if current_paragraph:
        merged_paragraphs.append(current_paragraph)

    final_text = '\n\n'.join(merged_paragraphs)
    return final_text



base_model = "PPL Chunking"
language = "en"
ppl_threshold = 0
chunk_length = 300
data_path = "./data/agriculture1.jsonl"#"example/data/examples.json"


def process_jsonl_file(file_path, base_model, language, ppl_threshold, chunk_length):

    with open(file_path, 'r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, start=1):
            try:
                data = json.loads(line)
                context = data.get('context')

                if context:
                    result = meta_chunking(context, base_model, language, ppl_threshold, chunk_length)
                    result_file_path = os.path.join(result_dir, f"line_{line_number}.txt")
                    with open(result_file_path, 'w', encoding='utf-8') as result_file:
                        result_file.write(result)
                    print(f"Chunking Result for line {line_number}: {result}")
                    print("-" * 80)

                else:
                    print(f"Warning: 'context' key not found in line {line_number}, skipping...")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in line {line_number}: {e}")
            except Exception as e:
                print(f"Error processing line {line_number}: {e}")



process_jsonl_file(data_path, base_model, language, ppl_threshold, chunk_length)