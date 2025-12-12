#!/usr/bin/env python3
"""Простой тест для проверки работы MCP сервера."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

async def test_mcp_server():
    """Тестирование MCP сервера."""
    # Загружаем переменные из .env файла
    from dotenv import load_dotenv
    env = os.environ.copy()
    load_dotenv()  # Загружаем в текущий процесс
    # Обновляем env с загруженными переменными
    for key, value in os.environ.items():
        env[key] = value
    
    server_params = StdioServerParameters(
        command="python",
        args=[str(Path(__file__).parent / "server.py")],
        env=env,
    )
    
    print("🚀 Запуск теста MCP сервера...")
    print("=" * 60)
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Инициализация
                print("\n📡 Инициализация сессии...")
                init_result = await session.initialize()
                print(f"✓ Инициализация завершена: {init_result.server_info.name if hasattr(init_result, 'server_info') else 'OK'}")
                
                # Получаем список инструментов
                print("\n🔧 Получение списка инструментов...")
                tools = await session.list_tools()
                print(f"✓ Найдено инструментов: {len(tools.tools)}")
                for tool in tools.tools:
                    print(f"  • {tool.name}: {tool.description[:60]}...")
                
                # Тест 1: Загрузка документа
                print("\n" + "=" * 60)
                print("📄 Тест 1: Загрузка документа")
                print("=" * 60)
                test_content = (
                    "Это тестовый документ для проверки работы MCP сервера. "
                    "Он содержит информацию о системе и её возможностях. "
                    "MCP сервер позволяет загружать документы, индексировать их "
                    "в OpenSearch и отвечать на вопросы на основе проиндексированных данных."
                )
                
                result = await session.call_tool(
                    "upload_document",
                    {
                        "content": test_content,
                        "source_name": "test_document.md"
                    }
                )
                print("Результат загрузки:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  {content.text}")
                    else:
                        print(f"  {content}")
                
                # Небольшая задержка для индексации
                print("\n⏳ Ожидание индексации (2 сек)...")
                await asyncio.sleep(2)
                
                # Тест 2: Поиск документов
                print("\n" + "=" * 60)
                print("🔍 Тест 2: Поиск документов")
                print("=" * 60)
                result = await session.call_tool(
                    "search_documents",
                    {
                        "query": "тестовый документ",
                        "max_results": 3
                    }
                )
                print("Результаты поиска:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  {content.text[:200]}...")
                    else:
                        print(f"  {content}")
                
                # Тест 3: Задать вопрос
                print("\n" + "=" * 60)
                print("❓ Тест 3: Задать вопрос")
                print("=" * 60)
                result = await session.call_tool(
                    "ask_question",
                    {
                        "question": "О чём этот документ?",
                        "max_results": 3
                    }
                )
                print("Ответ на вопрос:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  {content.text}")
                    else:
                        print(f"  {content}")
                
                print("\n" + "=" * 60)
                print("✅ Все тесты завершены успешно!")
                print("=" * 60)
                
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\nТест прерван")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
