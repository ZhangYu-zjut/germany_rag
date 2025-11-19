"""
德国议会智能问答系统 - 主程序
提供命令行交互界面
"""

import sys
from src.graph.workflow import QuestionAnswerWorkflow
from src.utils.logger import logger


def main():
    """主函数"""
    print("="*80)
    print("德国议会智能问答系统")
    print("="*80)
    print("\n欢迎使用！输入 'exit' 或 'quit' 退出系统")
    print("输入 'help' 查看帮助信息\n")
    
    # 初始化工作流
    try:
        print("正在初始化系统...")
        workflow = QuestionAnswerWorkflow()
        logger.info("工作流初始化成功")
        print("✅ 系统初始化成功\n")
    except Exception as e:
        logger.error(f"工作流初始化失败: {str(e)}")
        print(f"\n❌ 错误: 系统初始化失败")
        print(f"\n详细错误: {str(e)}")
        print("\n\u26a0️  请检查以下项目:")
        print("\n1. Milvus服务是否已启动")
        print("   - 检查: docker ps | grep milvus")
        print("   - 启动: docker start milvus")
        print("   - 或创建: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
        print("\n2. 环境变量配置是否正确 (.env文件)")
        print("   - OPENAI_API_KEY: 是否已设置")
        print("   - MILVUS_MODE: local 或 cloud")
        print("   - MILVUS_LOCAL_HOST: localhost")
        print("   - MILVUS_LOCAL_PORT: 19530")
        print("\n3. 是否已运行 build_index.py 构建索引")
        print("   - 运行: python build_index.py")
        print("   - 验证: python test_retrieval.py")
        print("\n4. Milvus Collection是否存在")
        print("   - Collection名称: parliament_speeches")
        print("   - 如果不存在,请先运行 build_index.py")
        
        import traceback
        print("\n\ud83d� 完整堆栈跟踪:")
        traceback.print_exc()
        return
    
    # 交互循环
    while True:
        try:
            # 获取用户输入
            question = input("\n请输入问题: ").strip()
            
            if not question:
                continue
            
            # 退出命令
            if question.lower() in ['exit', 'quit', '退出']:
                print("\n感谢使用！再见！")
                break
            
            # 帮助命令
            if question.lower() == 'help':
                print_help()
                continue
            
            # 处理问题
            print("\n正在处理您的问题...")
            result = workflow.run(question, verbose=True)
            
        except KeyboardInterrupt:
            print("\n\n感谢使用！再见！")
            break
        except Exception as e:
            logger.error(f"处理问题时发生错误: {str(e)}")
            print(f"\n错误: {str(e)}")
            print("请重新输入问题或输入 'help' 查看帮助")


def print_help():
    """打印帮助信息"""
    help_text = """
使用说明:
---------

1. 系统功能:
   - 回答关于德国联邦议院演讲记录的问题
   - 支持简单查询和复杂分析
   - 自动识别问题类型并选择最佳处理策略

2. 问题示例:

   简单查询:
   - "2019年德国联邦议院讨论了哪些主要议题?"
   - "Merkel在2020年3月15日说了什么?"
   - "CDU/CSU在2019年对气候保护的立场是什么?"

   复杂分析:
   - "在2015年到2018年期间,不同党派在难民问题上的立场有何变化?"
   - "请对比CDU/CSU和SPD在2019年对数字化政策的观点"
   - "请总结Merkel在2019年关于欧盟一体化的主要观点"

3. 支持的查询维度:
   - 时间: 年份、时间范围
   - 党派: CDU/CSU, SPD, FDP, GRÜNE, DIE LINKE, AfD
   - 议员: 具体议员姓名
   - 主题: 难民、气候、数字化、欧盟等

4. 命令:
   - 'help' - 显示此帮助信息
   - 'exit' 或 'quit' - 退出系统

5. 注意事项:
   - 当前数据范围: 2019-2021年 (PART模式)
   - 问题表述应尽量清晰具体
   - 系统会自动处理复杂问题的拆解
"""
    print(help_text)


if __name__ == "__main__":
    main()
