"""Build the editable presentation and a matching PDF/PNG preview.

Run: python -m pip install -r presentation/requirements.txt
     python presentation/build.py
"""
from pathlib import Path
import math
import os

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
PREVIEW = ROOT / ".local/doc-tasks/slide-previews"
W, H, PPI = 1600, 900, 120
BG, PANEL, WHITE, MUTED = "0C1A2B", "172D45", "F1F6FC", "ADC1D5"
MINT, ORANGE, BLUE = "7DD3C8", "F3B879", "8DA7CB"
FONT_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
NORMAL = FONT_DIR / "arial.ttf"
BOLD = FONT_DIR / "arialbd.ttf"
if not NORMAL.exists():
    NORMAL = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    BOLD = NORMAL.with_name("DejaVuSans-Bold.ttf")


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else NORMAL), size)


def color(value):
    return RGBColor.from_string(value)


def inch(pixels):
    return Inches(pixels / PPI)


class Canvas:
    def __init__(self, deck, number, title):
        self.slide = deck.slides.add_slide(deck.slide_layouts[6])
        self.slide.background.fill.solid()
        self.slide.background.fill.fore_color.rgb = color(BG)
        self.image = Image.new("RGB", (W, H), "#" + BG)
        self.draw = ImageDraw.Draw(self.image)
        self.number = number
        self.text(80, 47, 1380, 35, "PLATAFORMAS 2026.2  /  LOJA EM MICROSSERVIÇOS", 20, MINT, True)
        self.text(80, 107, 1450, 90, title, 61, WHITE, True)
        self.text(80, 851, 1330, 30, "projeto-microservicos.github.io/produto", 20, MUTED)
        self.text(1460, 849, 80, 32, f"{number:02}", 22, MINT, True)

    def rect(self, x, y, width, height, fill=PANEL, border=None):
        shape = self.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                            inch(x), inch(y), inch(width), inch(height))
        shape.adjustments[0] = 0.08
        shape.fill.solid()
        shape.fill.fore_color.rgb = color(fill)
        if border:
            shape.line.color.rgb = color(border)
            shape.line.width = Pt(1.2)
        else:
            shape.line.fill.background()
        self.draw.rounded_rectangle((x, y, x + width, y + height), radius=14,
                                    fill="#" + fill, outline=None if not border else "#" + border, width=2)

    def text(self, x, y, width, height, value, size=30, fill=WHITE, bold=False):
        selected = font(size, bold)
        lines = []
        for paragraph in value.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = (line + " " + word).strip()
                if line and selected.getlength(candidate) > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        spacing = round(size * 1.24)
        assert len(lines) * spacing <= height + 3, (self.number, value, len(lines), height)
        assert all(selected.getlength(line) <= width + 1 for line in lines), value
        box = self.slide.shapes.add_textbox(inch(x), inch(y), inch(width), inch(height))
        frame = box.text_frame
        frame.clear()
        frame.word_wrap = False
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.TOP
        for index, line in enumerate(lines):
            p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            p.text = line
            p.font.name = "Arial"
            p.font.size = Pt(size * 72 / PPI)
            p.font.bold = bold
            p.font.color.rgb = color(fill)
            p.space_before = p.space_after = Pt(0)
            p.line_spacing = Pt(spacing * 72 / PPI)
            self.draw.text((x, y + index * spacing), line, font=selected, fill="#" + fill)

    def line(self, x1, y1, x2, y2, fill=MINT, arrow=True):
        connector = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                                    inch(x1), inch(y1), inch(x2), inch(y2))
        connector.line.color.rgb = color(fill)
        connector.line.width = Pt(1.6)
        self.draw.line((x1, y1, x2, y2), fill="#" + fill, width=3)
        if arrow:
            angle = math.atan2(y2 - y1, x2 - x1)
            for delta in (-0.5, 0.5):
                ex, ey = x2 - 12 * math.cos(angle + delta), y2 - 12 * math.sin(angle + delta)
                self.line(x2, y2, ex, ey, fill, arrow=False)

    def node(self, x, y, width, label, detail, fill=PANEL, border=MINT):
        self.rect(x, y, width, 95, fill, border)
        self.text(x + 20, y + 14, width - 40, 42, label, 31, WHITE, True)
        self.text(x + 20, y + 57, width - 40, 28, detail, 20, MUTED)

    def notes(self, value):
        self.slide.notes_slide.notes_text_frame.text = value


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    deck = Presentation()
    deck.slide_width, deck.slide_height = inch(W), inch(H)
    deck.core_properties.title = "Loja em microsserviços — apresentação"
    deck.core_properties.subject = "Arquitetura no EKS e confirmação assíncrona de pedidos"
    deck.core_properties.author = "adventurescumm · João (joaorcmr)"
    deck.core_properties.comments = "Material de 19/11/2026, com assistência de IA declarada em docs/team.md."
    slides = []

    s = Canvas(deck, 1, "Uma loja. Seis serviços.")
    s.text(80, 253, 1060, 165, "Identidade, catálogo, pedidos e câmbio\ncom entrega independente no EKS.", 47, WHITE)
    s.text(1170, 220, 350, 255, "06", 185, MINT, True)
    s.text(80, 464, 1400, 90, "Do HTTP ao evento: o pedido responde antes da confirmação.", 36, MUTED)
    for x, title, detail in [(80, "EKS + RDS", "Aplicação e dados privados"),
                              (570, "GitHub Actions", "ECR + OIDC + imagem por digest"),
                              (1060, "RabbitMQ", "Outbox + consumidor idempotente")]:
        s.rect(x, 635, 460, 145)
        s.text(x + 25, 660, 410, 45, title, 32, MINT, True)
        s.text(x + 25, 717, 410, 45, detail, 23, MUTED)
    s.notes("00:00–00:10. Introduzir os seis microsserviços. Seguir a narração de docs/presentation.md. Não iniciar demonstração nesta tela.")
    slides.append(s)

    s = Canvas(deck, 2, "Do cliente ao cluster")
    s.text(80, 184, 1450, 44, "eks-store · us-east-2 · namespace store · 3 × t2.small", 27, MUTED)
    s.node(70, 248, 205, "Cliente", "Internet")
    s.line(275, 294, 350, 294)
    s.node(350, 248, 220, "NLB", "gateway-public")
    s.line(570, 294, 640, 294)
    s.node(640, 248, 240, "gateway", "rota + identidade", "164047")
    s.text(940, 269, 550, 70, "Única entrada pública\nDemais Services: ClusterIP", 26, MUTED)
    s.line(760, 343, 760, 383, arrow=False)
    s.line(180, 383, 1340, 383, arrow=False)
    for x in [180, 470, 760, 1050, 1340]:
        s.line(x, 383, x, 420)
    for x, label, detail in [(60, "auth", "access + refresh JWT"),
                               (350, "account", "contas + BCrypt"),
                               (640, "product", "catálogo em USD"),
                               (930, "order", "pedido + consumidor"),
                               (1220, "exchange", "PTAX + cache")]:
        s.node(x, 420, 240, label, detail)
    s.line(300, 467, 350, 467)
    s.line(930, 467, 880, 467)
    s.line(1170, 467, 1220, 467)
    for x in [470, 760, 1050]:
        s.line(x, 515, x, 568, BLUE, arrow=False)
    s.line(470, 568, 1050, 568, BLUE, arrow=False)
    s.line(610, 568, 610, 621, BLUE)
    s.rect(390, 625, 440, 105, "20324C", BLUE)
    s.text(414, 640, 400, 42, "RDS PostgreSQL privado", 30, WHITE, True)
    s.text(414, 687, 400, 30, "accounts · products · orders", 24, MUTED)
    s.line(1135, 515, 1135, 620, ORANGE)
    s.rect(940, 625, 520, 105, "41352B", ORANGE)
    s.text(965, 640, 470, 42, "RabbitMQ", 30, WHITE, True)
    s.text(965, 687, 470, 30, "relay → fila → consumidor em order", 23, MUTED)
    s.text(80, 779, 1440, 45, "GitHub Actions  →  ECR  →  EKS     |     OIDC e deploy por digest", 29, MINT, True)
    s.notes("00:10–00:30: arquitetura. 00:30–00:40: inserir trecho A com os pods no namespace store. 00:40–00:58: inserir trecho B do k6, CPU/HPA e réplicas. Gravação e edição por João no DOC-04. Aceleração ou cortes precisam ser identificados.")
    slides.append(s)

    s = Canvas(deck, 3, "Confirmar sem prender a requisição")
    s.rect(80, 246, 430, 200, "164047", MINT)
    s.text(110, 263, 370, 88, "201 Created", 57, MINT, True)
    s.text(110, 366, 370, 65, "Pedido e evento gravados\nna mesma transação", 25, WHITE)
    for x, title, detail in [(560, "Idempotência", "eventId evita repetir o efeito"),
                              (1050, "Recuperação", "falha do broker fica na outbox")]:
        s.rect(x, 246, 470, 200)
        s.text(x + 25, 278, 420, 48, title, 34, WHITE, True)
        s.text(x + 25, 354, 420, 65, detail, 27, MUTED)
    steps = [(80, 300, "Outbox", "evento persistido"),
             (440, 230, "Relay", "publica + retry"),
             (730, 280, "RabbitMQ", "orders.created"),
             (1070, 450, "Consumidor", "confirmação após o commit")]
    for index, (x, width, title, detail) in enumerate(steps):
        s.node(x, 530, width, title, detail, border=ORANGE if index == 2 else MINT)
        if index < len(steps) - 1:
            s.line(x + width, 578, steps[index + 1][0], 578)
    s.rect(80, 693, 1440, 102, "302D31")
    s.text(110, 715, 1370, 63, "Falhas transitórias → tentativas limitadas; mensagens inválidas → DLQ\nLimite atual: RabbitMQ em emptyDir. Próximo passo: armazenamento persistente.", 25, MUTED)
    s.notes("00:58–01:05: apresentar o gargalo de mensageria. 01:05–01:25: inserir trecho C real: POST 201, outbox com broker indisponível, recuperação e mensagem inválida na DLQ. Não afirmar exatamente uma entrega: o consumidor é idempotente e a entrega é pelo menos uma vez. Fonte: docs/mensageria.md.")
    slides.append(s)

    s = Canvas(deck, 4, "Entrega e próximos passos")
    s.rect(80, 246, 690, 366)
    s.text(110, 272, 630, 52, "Quem fez o quê", 36, MINT, True)
    s.text(110, 350, 630, 54, "adventurescumm · até 16/11", 30, WHITE, True)
    s.text(110, 405, 630, 65, "Order, exchange e material inicial de carga.", 27, MUTED)
    s.text(110, 483, 630, 48, "João · desde 17/11", 30, WHITE, True)
    s.text(110, 534, 630, 70, "Gateway, auth, account, product, AWS e integração.", 27, MUTED)
    s.rect(830, 246, 690, 366)
    s.text(860, 272, 630, 52, "Próximos passos", 36, ORANGE, True)
    s.text(860, 353, 620, 210, "01  Persistir o RabbitMQ com PVC\n\n02  Ampliar disponibilidade e réplicas\n\n03  Evoluir a revogação dos tokens", 28, WHITE)
    s.text(80, 665, 1440, 55, "Código, contratos e evidências na documentação", 36, WHITE, True)
    s.text(80, 735, 1440, 65, "Assistência de IA declarada nos READMEs.\nRoteiro e slides preparados por adventurescumm com apoio do Codex.", 25, MUTED)
    s.notes("01:25–01:50. Conclusão e próximos passos. Distinguir a implementação inicial de order/exchange por adventurescumm das evoluções feitas pelo João. O uso de IA está declarado nos READMEs e em docs/team.md. O roteiro reserva dez segundos até o limite de dois minutos.")
    slides.append(s)

    deck.save(OUT / "apresentacao.pptx")
    images = [s.image for s in slides]
    images[0].save(OUT / "apresentacao.pdf", save_all=True, append_images=images[1:], resolution=120)
    for index, image in enumerate(images, 1):
        image.save(PREVIEW / f"slide-{index}.png")
    contact = Image.new("RGB", (1600, 900), "#" + BG)
    for index, image in enumerate(images):
        contact.paste(image.resize((800, 450)), ((index % 2) * 800, (index // 2) * 450))
    contact.save(PREVIEW / "contact-sheet.png")
    print(f"Created {len(slides)} slides, editable PPTX, PDF and PNG previews")


if __name__ == "__main__":
    build()
