from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Literal, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import base64

Mode = Literal["Übergabe", "Rückgabe"]

@dataclass
class Employee:
    name: str = ""
    department: str = ""
    location: str = ""

@dataclass
class Item:
    name: str = ""
    serial: str = ""
    condition: str = ""
    note: str = ""

@dataclass
class ProtocolData:
    title: str
    date: str
    mode: Mode
    employee: Employee = field(default_factory=Employee)
    items: List[Item] = field(default_factory=list)
    notes: str = ""
    return_requirements: str = ""
    logo_b64: Optional[str] = None
    sig_giver_b64: Optional[str] = None
    sig_receiver_b64: Optional[str] = None
    giver_name: str = ""
    receiver_name: str = ""
    include_agreement: bool = False
    emp_street: str = ""
    emp_city: str = ""

class TemplateRenderer:
    def __init__(self, template_dir: Path) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_html(self, data: ProtocolData, template_name: str = "protocol_template.html") -> str:
        tmpl = self.env.get_template(template_name)
        return tmpl.render(
            title=data.title,
            date=data.date,
            mode=data.mode,
            employee=data.employee,
            items=data.items,
            notes=data.notes,
            return_requirements=data.return_requirements,
            logo_b64=data.logo_b64,
            sig_giver_b64=data.sig_giver_b64,
            sig_receiver_b64=data.sig_receiver_b64,
            giver_name=data.giver_name,
            receiver_name=data.receiver_name,
            include_agreement=data.include_agreement,
            emp_street=data.emp_street,
            emp_city=data.emp_city,
        )

def load_file_as_b64(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None
