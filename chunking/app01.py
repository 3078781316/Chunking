import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import torch.nn.functional as F
from chunk_rag import extract_by_html2text_db_nolist, split_text_by_punctuation



# 加载模型和分词器
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
        # 切割句子
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


# 示例数据
data_path = "example/data/examples.json"
with open(data_path, 'r', encoding='utf-8') as f:
    examples = json.load(f)


import os
input_folder = "example\input"
#from docx import Document

for filename in os.listdir(input_folder):

    file_path = os.path.join(input_folder, filename)
        # 打开 Word 文档

    # with open(file_path, "r", encoding='latin-1') as file:
    #     content = file.read()
    #     original_text = content
    #original_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    original_text = "Appendix A: Publications about Beekeeping\n\nAppendix B: Sources\n\nAppendix C: Glossary\n\n## **I NTRODUCTION**\n\nThe art, the craft, the science of beekeeping cannot be covered in a single book. The volume of information is simply too great. Furthermore, it is not necessary to learn everything the first year. However, you do need a certain broad exposure and a feeling for where you are headed. This book intends to give you that exposure and that sense of direction.\n\nWithout question, this is a book for beginners, although novices who have kept bees for a season or so can also benefit from it. It will take you through the first year, from spring to spring. Use the information here as a point of departure—and keep on reading about bees.\n\nAs with any endeavor, a certain amount of misinformation about bees and beekeeping is extant. Be selective in your reading and be hesitant in taking information on faith. Know your source, ask questions, and be sure the answers make sense.\n\nThis book is based on the experience of beekeeping in the northeastern United States. In this region, the active season for a honey bee colony begins in late April and extends through the end of September. Bees in other parts of the country have the same basic cycle, with adjustments in the calendar to reflect the climate and the specific forage available.\n\n## **CHAPTER 1 **\n\nBEFORE WE START\n\n**M** ost new beekeepers come into this exciting endeavor as hobbyists. Their whole attitude toward beekeeping is colored by this approach—it's relaxed, casual, and looks like fun—let's try it out. Beekeeping can be an enjoyable hobby. However, it can also be a disappointing failure. Beekeeping requires preparation, ongoing attention, and commitment. It requires knowledge—of bees, of growing things, and about the natural world in general. Beekeeping requires a certain amount of interaction with others in the beekeeping world, although this does not have to be an involved interaction.\n\n### **The Beekeeper's Commitment**\n\nToo many novice beekeepers do not recognize the level of commitment they must have. They do not know that, over the long run, for every beekeeper who succeeds, there are probably two or three who do not. How many of you have been in a classroom or a training program where the instructor says at the outset, \"Look at the person on your right; now look at the person on your left. One of you won't be here next year (or next week or next month).\" Beekeeping is like that.\n\nFurthermore, not all beekeepers are truly bee **keepers.** Some are bee **havers.** They develop an initial enthusiasm, acquire some bees, perhaps learn about them and work with them for a while, and then lose interest. Or perhaps they never develop any real knowledge or enthusiasm at all. One way or the other they become beehavers: they have some bees in the backyard but are not truly keeping them. The bees keep themselves. All may be well for a while, but in the long run, this seldom has a happy ending.\n\nTo be a successful beekeeper means to be a committed beekeeper, one who learns about the bees, comes to understand them, works with them on a regular basis, and enjoys them. If you believe your involvement might be something less than this, perhaps beekeeping is not for you.\n\nIt is difficult to keep bees if you don't have contact at some level with other beekeepers and with sources of new developments—government agencies; universities; and local, state, or national beekeeper organizations. All of these sources are an important part of the overall beekeeping picture. Contact can be as simple as membership in a beekeepers' club or association or regular reading of a beekeepers' magazine. Taking both approaches is not too much. Beekeeping is a dynamic endeavor. Problems arise, solutions are worked out, research is undertaken, new knowledge comes to the fore continually. Knowledge of bees and of beekeeping has increased immensely in recent years, as have the problems. A beekeeper who is out of touch will be quickly overwhelmed.\n\nSome individuals who take up beekeeping do so because they need bees for pollination. They want bees on their property to take care of their crops, whether it be a small home garden or a commercial operation. They need the bees to ensure an adequate crop. Their approach is to obtain one or several colonies, put the bees out in a corner of the property, and forget about them, assuming they will take care of themselves. And the bees will, for a while. But the facts of bee life—disease, drought, an unusually harsh winter, predators, any or all of these problems and others—can cause the colony to weaken and to die. It happens regularly in nature. We don't think about it because we don't see it, but a colony of honey bees often has a tenuous grip on life in North America, especially in the more northerly regions. Feral colonies die regularly. They are replaced almost as regularly by swarms from other feral colonies or from a beekeeper's holdings. But this is not a desirable situation. We are not in control, and with the problems mentioned earlier, we must be. Someone who wants bees on his or her property, but does not wish to care for them, should think seriously of finding a beekeeper who is willing to establish colonies on the property in question: It is a much more satisfactory approach in the long run. With all of these thoughts in mind, let's now prepare to get started.\n\n### **Dimensions of Beekeeping**\n\nBeekeeping is multifaceted. It is much more than placing a hive in the backyard, visiting it a couple of times a year, and reaping the benefits in terms of honey and pollination. I will discuss the actual benefits, the returns, later on, but for now, what must go into this new endeavor? What are the dimensions, the scope, of the activity you are about to undertake? How much time is involved? What is the cost? In what ways will it be restrictive? We will address each of these in turn.\n\n#### **Time**\n\nThe time devoted to keeping bees does not have to be great. It may be only a few hours per year—once you are past the initial learning period. Of course, it also might be many hours. As with most endeavors, what you get back is proportionate to what you put in. Furthermore, some people have different goals when they take up with bees.\n\nNo matter what your goals, the first time commitment should be to learning. This is accomplished by reading, attending an informal bee school and a workshop or two, attending occasional club or association meetings, and talking with other beekeepers. Many individuals undertake beekeeping with a minimum of preparation, believing that they can just dive in and pick up the requisite knowledge on the fly. It doesn't work that way. Success comes only after the acquisition of basic knowledge. Plan on a commitment of learning time that will be heavy during the first year or so and less as time passes.\n\nGiven a basic level of understanding and a willingness to continue learning at a modest level, you should plan on visiting your bees at least once every 2 weeks during the active season, perhaps more often in the spring as the new season is getting underway and certainly less often in the winter. However, bees should never be totally ignored, even in winter. Life goes on in the colony year-round.\n\nIndividual visits per hive may be quite brief, depending on the season and your reason for being at the hive. Some visits may last a minute or two; others involving a specific task may last 20 to 30 minutes per hive, although usually not longer. Most visits that involve opening the hive are a substantial disruption to colony life but serve an important purpose. Although you can skip visits now and then (beekeepers are allowed to go on vacation), ignoring the bees for weeks on end only leads to problems. Some endeavors or hobbies can be picked up or put down at will. Beekeeping is different. Chores not done at the proper time usually cannot be done as well later, if they can be done at all.\n\nAll in all, the time involved in keeping bees is not great, once you are past the first year. The dimensions of the involvement should become clearer as you progress through the book. But the intensity of this effort deserves some thought.\n\n#### **Money**\n\nWhy are you going to keep bees? Most new beekeepers see it as an interesting hobby, and if they can make money on the side, so much the better. Others go into it with the specific intent of making money: a new beekeeper seldom does. An experienced beekeeper may, but no one should count on it. Far too many variables and problems exist for any beekeeper to ever be completely in control. Go into beekeeping strictly as a hobby. Expect it to cost money. Initially, it will be all outgo. If, after a couple of years, you have surplus honey to sell—that's wonderful. In time, you may even have enough hives to go into crop pollination in a small way. Eventually, if all is going well, perhaps you can turn this hobby into a sideline business, but don't base your future on it now. Wait until you see what it's all about.\n\nSo, how is the first season going to treat your pocketbook? I'll throw out a ballpark figure now and address this topic in a little more detail in the section on equipment. For now, assume an expenditure of $150 to $200, depending on sources and quality, to set up a complete hive with a couple of honey supers, bees included. Necessary additional equipment, such as smoker, hive tool, veil, and so on, may cost another $60 to $75. Although in the past it was sometimes possible to recover part of this investment through honey production during the first or second season, it is highly unlikely that you can do so in today's economy. In recent years, the cost of beekeeping equipment and supplies has risen much, much faster than the value of honey.\n\n#### **The Down Side**\n\nBeekeeping is not all pleasure. It does have a down side—as most things in life do.\n\nSome beekeepers have a partner and they work their hives together. However, most beekeepers are loners. You will be out there by yourself, in the heat, sticky to your elbows, bees buzzing about, a veil in place so you can't scratch or blow your nose or take a drink of water. Occasionally, you will infuriate the bees, and they will find ways to get under your veil, up your sleeves, or into some other place you might not want to discuss in polite company. There is nothing more disconcerting than to realize that a bee is inside your pants, crawling up your leg, and already at knee level. As you move about, your clothing is eventually going to pinch the bee and cause it to sting. You have two choices: leave the beeyard and disrobe carefully so the bee can escape, or slap where the bee is and kill it. It won't go away by itself.\n\nDo not discount the heat, the weight of the equipment, and the discomfort of work in a beeyard. These discomforts are not a regular feature of beekeeping, but there are times when you will find yourself wondering what you are doing in this position, the hive open and its parts strewn about you, bees everywhere, sweat streaming—and suddenly, you realize that there is a bee inside the veil. But like so many negative experiences, it will be soon forgotten. You will go back there again and have a great time. Just be aware that life in the beeyard does have its challenges.\n\n#### **The Up Side**\n\nWithout question, there is an up "
    base_model = "PPL Chunking"
    language = "en"
    ppl_threshold = 0
    chunk_length = 300
    result_text = meta_chunking(original_text, base_model, language, ppl_threshold, chunk_length)
    print(f"Original Text: {original_text}")
    print(f"Chunking Result: {result_text}")
    print("-" * 80)



## 测试每个示例
# for example in examples:
#     original_text = example['original_text']
#     base_model = example['base_model']
#     language = example['language']
#     ppl_threshold = example['ppl_threshold']
#     chunk_length = example['chunk_length']

#     result_text = meta_chunking(original_text, base_model, language, ppl_threshold, chunk_length)
#     print(f"Sample ID: {example['idx']}")
#     print(f"Original Text: {original_text}")
#     print(f"Chunking Result: {result_text}")
#     print("-" * 80)