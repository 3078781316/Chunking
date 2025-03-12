package com.group85.financetracker.gui;


import com.group85.financetracker.model.Transaction;
import com.group85.financetracker.service.TransactionService;
import com.group85.financetracker.service.AIClassificationService;
import com.group85.financetracker.repository.FileRepository;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public class FinanceTrackerGUI extends JFrame {
    private TransactionService transactionService;
    private AIClassificationService aiClassificationService;
    private FileRepository fileRepository;
    private JTable transactionTable;
    private DefaultTableModel tableModel;

    public FinanceTrackerGUI() {
        super("AI-Empowered Personal Finance Tracker");
        transactionService = new TransactionService();
        aiClassificationService = new AIClassificationService();
        fileRepository = new FileRepository("transactions.csv");

        // 加载之前保存的交易数据
        List<Transaction> loadedTransactions = fileRepository.loadTransactions();
        transactionService.importTransactions(loadedTransactions);

        // 设置窗口属性
        setSize(800, 600);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        // 创建表格模型
        tableModel = new DefaultTableModel();
        tableModel.setColumnIdentifiers(new Object[]{"ID", "Description", "Amount", "Category", "Date"});

        // 创建表格
        transactionTable = new JTable(tableModel);
        JScrollPane scrollPane = new JScrollPane(transactionTable);
        add(scrollPane, BorderLayout.CENTER);

        // 创建输入面板
        JPanel inputPanel = new JPanel();
        inputPanel.setLayout(new BoxLayout(inputPanel, BoxLayout.Y_AXIS));

        // 输入字段
        JTextField descriptionField = new JTextField(20);
        JTextField amountField = new JTextField(10);
        JTextField dateField = new JTextField(10);
        dateField.setText(LocalDate.now().toString());

        // 添加交易按钮
        JButton addTransactionButton = new JButton("Add Transaction");
        addTransactionButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String description = descriptionField.getText();
                double amount;
                try {
                    amount = Double.parseDouble(amountField.getText());
                } catch (NumberFormatException ex) {
                    JOptionPane.showMessageDialog(FinanceTrackerGUI.this,
                            "Invalid amount format", "Error", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                String dateString = dateField.getText();
                LocalDate date;
                try {
                    date = LocalDate.parse(dateString);
                } catch (Exception ex) {
                    JOptionPane.showMessageDialog(FinanceTrackerGUI.this,
                            "Invalid date format", "Error", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                // 创建新交易
                String id = UUID.randomUUID().toString().substring(0, 8);
                Transaction transaction = new Transaction(id, description, amount, "", date);

                // 使用AI分类
                String category = aiClassificationService.classifyTransaction(transaction);
                transaction.setCategory(category);

                // 添加到服务和表格
                transactionService.addTransaction(transaction);
                tableModel.addRow(new Object[]{id, description, amount, category, date});

                // 保存到文件
                fileRepository.saveTransactions(transactionService.getAllTransactions());

                // 清空输入字段
                descriptionField.setText("");
                amountField.setText("");
                dateField.setText(LocalDate.now().toString());
            }
        });

        // 创建表单布局
        inputPanel.add(createFormPanel("Description:", descriptionField));
        inputPanel.add(createFormPanel("Amount:", amountField));
        inputPanel.add(createFormPanel("Date (YYYY-MM-DD):", dateField));
        inputPanel.add(addTransactionButton);

        add(inputPanel, BorderLayout.EAST);

        // 初始化表格数据
        updateTable();

        setVisible(true);
    }

    private JPanel createFormPanel(String labelText, JTextField textField) {
        JPanel panel = new JPanel();
        panel.setLayout(new BorderLayout());
        panel.setBorder(BorderFactory.createEmptyBorder(0, 5, 0, 5)); // 添加左右间距
        panel.add(new JLabel(labelText), BorderLayout.WEST);
        panel.add(textField, BorderLayout.CENTER);
        return panel;
    }

    private void updateTable() {
        // 清空表格
        tableModel.setRowCount(0);

        // 添加所有交易到表格
        for (Transaction transaction : transactionService.getAllTransactions()) {
            tableModel.addRow(new Object[]{
                    transaction.getId(),
                    transaction.getDescription(),
                    transaction.getAmount(),
                    transaction.getCategory(),
                    transaction.getDate()
            });
        }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(new Runnable() {
            @Override
            public void run() {
                new FinanceTrackerGUI();
            }
        });
    }
}