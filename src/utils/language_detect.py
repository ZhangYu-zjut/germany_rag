"""
语言检测工具
简单判断用户输入是中文还是德文
"""

import re


def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 输入文本
        
    Returns:
        'zh' (中文) 或 'de' (德文)
    """
    # 移除空格和标点
    text_clean = re.sub(r'[^\w]', '', text)
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text_clean))
    
    # 统计德文特殊字符（ä, ö, ü, ß等）
    german_chars = len(re.findall(r'[äöüßÄÖÜ]', text))
    
    # 统计总字符数
    total_chars = len(text_clean)
    
    if total_chars == 0:
        return 'zh'  # 默认中文
    
    # 中文字符比例
    chinese_ratio = chinese_chars / total_chars
    
    # 如果中文字符超过30%，判断为中文
    if chinese_ratio > 0.3:
        return 'zh'
    
    # 如果有德文特殊字符，判断为德文
    if german_chars > 0:
        return 'de'
    
    # 检查常见德文词
    german_keywords = [
        'wie', 'was', 'welche', 'welcher', 'wann', 'warum', 
        'der', 'die', 'das', 'und', 'oder', 
        'Bundestag', 'Partei', 'Politik', 'Jahr',
        'zwischen', 'haben', 'wurde', 'wurden'
    ]
    
    text_lower = text.lower()
    german_word_count = sum(1 for word in german_keywords if word.lower() in text_lower)
    
    # 如果有3个以上德文关键词，判断为德文
    if german_word_count >= 3:
        return 'de'
    
    # 默认中文
    return 'zh'


def get_system_capabilities(language: str = None, question: str = None) -> str:
    """
    获取系统功能说明（根据语言选择）
    
    Args:
        language: 'zh' 或 'de'，如果为None则根据question自动检测
        question: 用户问题，用于自动检测语言
        
    Returns:
        系统功能说明文本
    """
    from src.llm.prompts_fallback import FallbackPrompts
    
    # 如果没有指定语言，尝试检测
    if language is None and question:
        language = detect_language(question)
    
    # 默认中文
    if language is None:
        language = 'zh'
    
    if language == 'de':
        return FallbackPrompts.SYSTEM_CAPABILITIES_DE
    else:
        return FallbackPrompts.SYSTEM_CAPABILITIES


if __name__ == "__main__":
    # 测试语言检测
    test_cases = [
        ("你会做什么？", "zh"),
        ("Was können Sie tun?", "de"),
        ("2019年德国议会讨论了哪些议题？", "zh"),
        ("Welche Themen wurden 2019 im Bundestag diskutiert?", "de"),
        ("Wie haben sich die Positionen zur Flüchtlingspolitik verändert?", "de"),
        ("请总结绿党的立场", "zh"),
    ]
    
    print("=== 语言检测测试 ===\n")
    for text, expected in test_cases:
        detected = detect_language(text)
        status = "✅" if detected == expected else "❌"
        print(f"{status} \"{text}\"")
        print(f"   检测: {detected}, 期望: {expected}\n")

