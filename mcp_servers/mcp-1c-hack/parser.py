"""Парсер выгруженной конфигурации 1С в индекс поиска."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from lxml import etree

TYPE_MAP: Dict[str, str] = {
    "Catalogs": "Catalog",
    "Documents": "Document",
    "Reports": "Report",
    "DataProcessors": "DataProcessor",
    "InformationRegisters": "InformationRegister",
    "AccumulationRegisters": "AccumulationRegister",
    "ChartsOfAccounts": "ChartOfAccounts",
}


def _get_text_by_local(root: etree._Element, local_name: str) -> str:
    """Возвращает текст первого узла по local-name независимо от пространства имен."""
    try:
        values = root.xpath(f"//*[local-name()='{local_name}']/text()")
        if values:
            return (values[0] or "").strip()
    except Exception:
        pass
    return ""


def _get_synonym(root: etree._Element) -> str:
    """Извлекает синоним, предпочитая ru."""
    try:
        items = root.xpath(".//*[local-name()='Synonym']//*[local-name()='item']")
    except Exception:
        return ""
    best = ""
    for item in items:
        text = "".join(item.itertext()).strip()
        lang = (item.get("lang") or "").lower()
        if lang == "ru" and text:
            return text
        if text and not best:
            best = text

    # Fallback: иногда content лежит напрямую
    try:
        contents = root.xpath(".//*[local-name()='Synonym']//*[local-name()='content']")
    except Exception:
        contents = []
    for content in contents:
        text = "".join(content.itertext()).strip()
        if text:
            return text

    return best


def parse_folder(base_dir: Path) -> List[Dict[str, str]]:
    """
    Сканирует выгруженную конфигурацию и возвращает индекс объектов.

    Args:
        base_dir: Каталог с выгруженной конфигурацией (DumpConfigToFiles).

    Returns:
        Список словарей: {'name', 'synonym', 'type', 'search_text'}.
    """

    index: List[Dict[str, str]] = []
    if not base_dir.exists():
        return index

    for folder, type_name in TYPE_MAP.items():
        type_dir = base_dir / folder
        if not type_dir.exists():
            continue

        for xml_path in type_dir.rglob("*.xml"):
            try:
                parts_lower = [p.lower() for p in xml_path.parts]
                if "forms" in parts_lower:
                    continue

                is_metadata = xml_path.name.lower() == "metadata.xml"
                is_direct = xml_path.parent == type_dir
                if not (is_direct or is_metadata):
                    continue

                tree = etree.parse(str(xml_path))
                root = tree.getroot()
                name = _get_text_by_local(root, "Name")
                synonym = _get_synonym(root)

                # Формы для объекта
                forms = _collect_forms(xml_path, type_dir)
                form_tokens: List[str] = []
                for form in forms:
                    form_tokens.append(form.get("name", ""))
                    form_tokens.append(form.get("synonym", ""))

                search_text = " ".join([name, synonym, type_name] + form_tokens).strip().lower()

                index.append(
                    {
                        "name": name,
                        "synonym": synonym,
                        "type": type_name,
                        "forms": forms,
                        "search_text": search_text,
                    }
                )
            except Exception:
                continue

    return index


def _collect_forms(xml_path: Path, type_dir: Path) -> List[Dict[str, str]]:
    """
    Собирает имена и синонимы форм для объекта, если они присутствуют в папке Forms.
    """

    # Определяем каталог объекта
    if xml_path.name.lower() == "metadata.xml":
        obj_dir = xml_path.parent.parent  # .../<Obj>/Ext/Metadata.xml -> <Obj>
    elif xml_path.parent == type_dir:
        obj_dir = type_dir / xml_path.stem  # Catalogs/Name.xml -> Catalogs/Name/Forms
    else:
        obj_dir = xml_path.parent

    forms_dir = obj_dir / "Forms"
    forms: List[Dict[str, str]] = []
    if not forms_dir.exists():
        return forms

    for form_xml in forms_dir.rglob("*.xml"):
        try:
            tree = etree.parse(str(form_xml))
            root = tree.getroot()
            form_name = _get_text_by_local(root, "Name")
            form_synonym = _get_synonym(root)
            forms.append(
                {
                    "name": form_name,
                    "synonym": form_synonym,
                    "path": str(form_xml),
                }
            )
        except Exception:
            continue

    return forms
