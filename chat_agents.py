import openai
import os
import re
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from pydantic_ai import Agent
import requests
from datetime import datetime

# Carregar variáveis do ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Funções Auxiliares ---

def wrap_xml(agent_name: str, content: str, tag: str = "content") -> str:
    root = ET.Element("result")
    agent_elem = ET.SubElement(root, "agent")
    agent_elem.text = agent_name
    content_elem = ET.SubElement(root, tag)
    content_elem.text = content
    return ET.tostring(root, encoding="unicode")

def extract_tag_content(xml_str: str, tag: str = "content") -> str:
    root = ET.fromstring(xml_str)
    elem = root.find(tag)
    return elem.text if elem is not None else ""

def clean_markdown_code(code: str) -> str:
    """
    Remove blocos de código Markdown (```) do código gerado.
    """
    code = re.sub(r'```[\w]*\n?', '', code)
    code = re.sub(r'```', '', code)
    code = re.sub(r'(^|\n)#+\s*.*', '', code)
    code = re.sub(r'(^|\n)(Claro!|Abaixo|Aqui está|Segue|Pronto).*?:\n', '\n', code, flags=re.IGNORECASE)
    code = code.strip()
    return code

# Para dados estruturados de produtos
def wrap_products(products: list) -> str:
    root = ET.Element("products")
    for prod in products:
        prod_elem = ET.SubElement(root, "product")
        nome_elem = ET.SubElement(prod_elem, "nome")
        nome_elem.text = prod["nome"]
        desc_elem = ET.SubElement(prod_elem, "descricao")
        desc_elem.text = prod["descricao"]
        preco_elem = ET.SubElement(prod_elem, "preco")
        preco_elem.text = str(prod["preco"])
    return ET.tostring(root, encoding="unicode")

def extract_products(xml_str: str) -> list:
    root = ET.fromstring(xml_str)
    products = []
    for prod_elem in root.findall("product"):
        nome = prod_elem.find("nome").text
        descricao = prod_elem.find("descricao").text
        preco = float(prod_elem.find("preco").text)
        products.append({"nome": nome, "descricao": descricao, "preco": preco})
    return products

# Para dados estruturados de imagens
def wrap_images(images: list) -> str:
    root = ET.Element("images")
    for img in images:
        img_elem = ET.SubElement(root, "image")
        pname_elem = ET.SubElement(img_elem, "product_name")
        pname_elem.text = img["product_name"]
        url_elem = ET.SubElement(img_elem, "image_url")
        url_elem.text = img["image_url"]
    return ET.tostring(root, encoding="unicode")

def extract_images(xml_str: str) -> list:
    root = ET.fromstring(xml_str)
    images = []
    for img_elem in root.findall("image"):
        product_name = img_elem.find("product_name").text
        image_url = img_elem.find("image_url").text
        images.append({"product_name": product_name, "image_url": image_url})
    return images

def download_and_save_image(image_url: str, product_name: str) -> str or None:
    """
    Faz download da imagem e a salva localmente no diretório 'static/images'.
    Retorna a URL local relativa.
    """
    try:
        # Criar diretório se não existir
        os.makedirs('static/images', exist_ok=True)
        
        # Fazer download
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Gerar nome único para o arquivo
        safe_name = re.sub(r'[^\w\-_\.]', '_', product_name).lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_name}_{timestamp}.png"
        filepath = os.path.join('static/images', filename)
        
        # Salvar arquivo
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # Retornar URL local (relativa)
        return f"/static/images/{filename}"
    
    except Exception as e:
        print(f"❌ Erro ao fazer download da imagem para '{product_name}': {e}")
        return None

# --- Agentes ---

class TextGeneratorAgent(Agent):
    def respond(self, topic: str) -> str:
        prompt = f"Descreva um contexto detalhado sobre o seguinte produto para um e-commerce: {topic}."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content
        print("\n🔍 Resposta do TextGeneratorAgent:\n", response_text)
        return wrap_xml("TextGeneratorAgent", response_text)

class UXResearchAgent(Agent):
    def respond(self, context_xml: str) -> str:
        context = extract_tag_content(context_xml)
        prompt = f"Baseado neste contexto de produto: {context}, crie uma persona do cliente ideal. Inclua dores, necessidades e oportunidades para esse público."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content
        print("\n🔍 Resposta do UXResearchAgent:\n", response_text)
        return wrap_xml("UXResearchAgent", response_text)

class UXDesignerAgent(Agent):
    def respond(self, persona_xml: str) -> str:
        persona = extract_tag_content(persona_xml)
        prompt = (
            f"Com base nesta persona: {persona}, descreva os melhores elementos de UX para a página do e-commerce. "
            "Inclua:\n- Tipo de fonte ideal\n- Disposição das imagens\n- Estrutura para conversão de vendas\n- Paleta de cores recomendada\n"
            "NÃO mencione logo ou marca visual. Foque apenas em layout, tipografia, cores e disposição de elementos."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content
        print("\n🔍 Resposta do UXDesignerAgent:\n", response_text)
        return wrap_xml("UXDesignerAgent", response_text)

class BusinessAgent(Agent):
    """
    Agente de Negócios: Limita a 3 produtos.
    """
    def respond(self, persona_xml: str) -> str:
        persona = extract_tag_content(persona_xml)
        prompt = (
            f"Com base nesta persona: {persona}, crie uma lista de EXATAMENTE 3 produtos ideais para o e-commerce. Para cada produto, forneça:\n"
            "- Nome\n- Descrição curta\n- Preço sugerido (em USD)\n"
            "Formato esperado (3 linhas apenas):\nProduto 1 | Descrição 1 | 199.99\nProduto 2 | Descrição 2 | 299.99\nProduto 3 | Descrição 3 | 399.99"
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content.strip()
        
        products = []
        for line in response_text.split("\n"):
            parts = line.split(" | ")
            if len(parts) == 3:
                try:
                    products.append({
                        "nome": parts[0].strip(),
                        "descricao": parts[1].strip(),
                        "preco": float(parts[2].strip())
                    })
                except ValueError:
                    print(f"⚠️ Erro ao converter preço: {parts[2]}")
        
        products = products[:3]
        
        print(f"✅ BusinessAgent: {len(products)} produtos gerados. Lista:")
        for p in products:
            print(f"   - {p['nome']} (Descrição: {p['descricao']}, Preço: ${p['preco']:.2f})")
            
        return wrap_products(products)

class PhotographerAgent(Agent):
    """
    Agente Fotógrafo: Limita a 3 imagens e faz download local.
    """
    def respond(self, products_xml: str) -> str:
        products = extract_products(products_xml)
        products = products[:3]
        
        images = []
        print(f"🖼️ Iniciando a geração de {len(products)} imagens para os produtos...")
        
        for idx, product in enumerate(products, 1):
            prompt = f"Imagem realista de um {product['nome']} em fundo branco, otimizada para e-commerce."
            print(f"🖼️ [{idx}/{len(products)}] Gerando imagem para '{product['nome']}'...")
            
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024"
                )
                
                image_url_dalle = response.data[0].url
                
                # FAZ DOWNLOAD E SALVA LOCALMENTE
                local_url = download_and_save_image(image_url_dalle, product['nome'])
                
                if local_url:
                    print(f"✅ Imagem gerada e salva localmente: {local_url}")
                    images.append({
                        "product_name": product["nome"],
                        "image_url": local_url  # Usa a URL local
                    })
                
            except Exception as e:
                print(f"❌ Erro ao gerar ou salvar imagem para '{product['nome']}': {str(e)}")
        
        print(f"✅ PhotographerAgent: {len(images)} imagens processadas com sucesso")
        return wrap_images(images)

class SpecificationAgent(Agent):
    def respond(self, persona_xml: str, ux_elements_xml: str, images_xml: str) -> str:
        persona = extract_tag_content(persona_xml)
        ux_elements = extract_tag_content(ux_elements_xml)
        images = extract_images(images_xml)
        image_info = "\n".join([f"{img['product_name']}: {img['image_url']}" for img in images])
        
        prompt = (
            f"VOCÊ É UM ESPECIALISTA EM DESIGN E ESPECIFICAÇÃO TÉCNICA DE E-COMMERCE.\n\n"
            f"Com base na seguinte persona de cliente:\n{persona}\n\n"
            f"E nos seguintes elementos de UX recomendados:\n{ux_elements}\n\n"
            f"Crie uma ESPECIFICAÇÃO TÉCNICA EXTREMAMENTE DETALHADA para um e-commerce que atenda perfeitamente essa persona.\n\n"
            f"As imagens do site serão:\n{image_info}\n\n"
            f"IMPORTANTE: NÃO inclua nenhuma especificação de logo ou marca visual. Foque apenas em layout, cores, tipografia e componentes.\n\n"
            f"VOCÊ DEVE FORNECER (em formato estruturado e claro):\n"
            f"1. PALETA DE CORES EXATA:\n"
            f"   - Cor primária (com código HEX): [use uma cor que reflita a persona]"
            f"   - Cor secundária (com código HEX): [complementar]"
            f"   - Cor de destaque (com código HEX): [para CTAs]"
            f"   - Cor de fundo (com código HEX): [branco, cinza claro, etc]"
            f"   - Cor de texto (com código HEX): [escuro para legibilidade]"
            f"\n2. TIPOGRAFIA:\n"
            f"   - Fonte para títulos: [ex: Montserrat, Playfair Display, etc]"
            f"   - Tamanho de título (h1): [ex: 48px]"
            f"   - Tamanho de subtítulo (h2): [ex: 32px]"
            f"   - Fonte para corpo: [ex: Open Sans, Lato, etc]"
            f"   - Tamanho de corpo: [ex: 16px]"
            f"   - Peso das fontes: [ex: 400 para corpo, 700 para títulos]"
            f"\n3. LAYOUT E ESTRUTURA:\n"
            f"   - Cabeçalho: [descrição do design]"
            f"   - Seção de produtos: [grid 3 colunas, cards com sombra, etc]"
            f"   - Rodapé: [cor, conteúdo]"
            f"   - Espaçamento entre elementos: [padding, margin]"
            f"   - Largura máxima do container: [ex: 1200px]"
            f"\n4. COMPONENTES:\n"
            f"   - Botões: [cor, tamanho, hover effect]"
            f"   - Cards de produto: [altura, sombra, efeito ao passar mouse]"
            f"   - Imagens: [tamanho, border-radius, object-fit]"
            f"\n5. EFEITOS E INTERATIVIDADE:\n"
            f"   - Transições: [duração, tipo]"
            f"   - Hover effects: [descrever para botões e cards]"
            f"   - Responsividade: [breakpoints para mobile, tablet, desktop]"
            f"\nFORNEÇA A ESPECIFICAÇÃO DE FORMA ESTRUTURADA E CLARA, PARA QUE POSSA SER DIRETAMENTE APLICADA NO CSS."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content
        print("\n🔍 Resposta do SpecificationAgent:\n", response_text)
        return wrap_xml("SpecificationAgent", response_text, tag="specification")

class CodeGeneratorAgent(Agent):
    """
    Agente Gerador de Código: Gera apenas o conteúdo do <body> e remove blocos Markdown.
    CRÍTICO: Deve aplicar OBRIGATORIAMENTE as especificações de cores, tipografia e layout.
    NOVO: Recebe também os dados dos produtos para gerar descrições reais.
    """
    def respond(self, specification_xml: str, images_xml: str, products_xml: str = None) -> str:
        specification = extract_tag_content(specification_xml, tag="specification")
        images = extract_images(images_xml)
        
        # Extrair dados dos produtos se fornecidos
        products = []
        products_info = ""
        if products_xml:
            products = extract_products(products_xml)
            products_info = "\n".join([
                f"- {p['nome']}: {p['descricao']} (Preco: ${p['preco']:.2f})"
                for p in products
            ])
        
        # Criar mapa de imagens por nome de produto
        image_map = {img['product_name']: img['image_url'] for img in images}
        
        # Gerar tags de imagem com dados reais dos produtos
        image_tags = ""
        if products:
            image_tags = "\n".join([
                f'<img src="{image_map.get(p["nome"], "")}" alt="{p["nome"]}" style="width:200px; height:auto; object-fit: cover;">'
                for p in products
            ])
        else:
            image_tags = "\n".join([
                f'<img src="{img["image_url"]}" alt="{img["product_name"]}" style="width:200px; height:auto; object-fit: cover;">'
                for img in images
            ])
        
        prompt = (
            f"VOCE E UM ESPECIALISTA EM DESENVOLVIMENTO WEB E DESIGN FRONT-END.\n\n"
            f"Sua tarefa e GERAR O CODIGO HTML/CSS COMPLETO para um e-commerce baseado na seguinte especificacao:\n\n"
            f"{specification}\n\n"
        )
        
        # Adicionar informações dos produtos se disponíveis
        if products_info:
            prompt += (
                f"PRODUTOS REAIS DO E-COMMERCE (USE EXATAMENTE ESTES DADOS):\n{products_info}\n\n"
                f"As imagens do site devem ser inseridas usando EXATAMENTE estas tags:\n{image_tags}\n\n"
            )
        else:
            prompt += (
                f"As imagens do site devem ser inseridas usando EXATAMENTE estas tags:\n{image_tags}\n\n"
            )
        
        prompt += (
            f"INSTRUCOES CRITICAS - VOCE DEVE SEGUIR RIGOROSAMENTE:\n\n"
            f"1. APLICAR CORES:\n"
            f"   - Extraia os codigos HEX de cores da especificacao acima\n"
            f"   - Aplique OBRIGATORIAMENTE essas cores no CSS (backgrounds, textos, botoes, etc)\n"
            f"   - Nao use cores genericas; use EXATAMENTE as cores especificadas\n\n"
            f"2. APLICAR TIPOGRAFIA:\n"
            f"   - Extraia as fontes e tamanhos da especificacao\n"
            f"   - Use @import do Google Fonts se necessario\n"
            f"   - Aplique os tamanhos e pesos EXATAMENTE como especificado\n\n"
            f"3. APLICAR LAYOUT:\n"
            f"   - Siga a estrutura de layout descrita (cabecalho, produtos, rodape, etc)\n"
            f"   - Use grid ou flexbox conforme especificado\n"
            f"   - Aplique espacamentos (padding, margin) como indicado\n\n"
            f"4. USAR DADOS REAIS DOS PRODUTOS:\n"
            f"   - Se produtos foram fornecidos, use EXATAMENTE os nomes, descricoes e precos reais\n"
            f"   - NAO use placeholders como 'Produto 1' ou 'Descricao do Produto 1'\n"
            f"   - Cada card deve exibir o nome real, descricao real e preco real do produto\n\n"
            f"5. COMPONENTES:\n"
            f"   - Botoes: com cores e efeitos hover especificados\n"
            f"   - Cards: com sombras, bordas e efeitos conforme especificacao\n"
            f"   - Imagens: com tamanhos e estilos especificados\n\n"
            f"6. RESPONSIVIDADE:\n"
            f"   - Inclua media queries para mobile, tablet e desktop\n"
            f"   - Garanta que o layout se adapte bem em todos os tamanhos\n\n"
            f"7. FORMATO DO CODIGO:\n"
            f"   - Gere APENAS o conteudo do <body> (sem <!DOCTYPE>, <html>, <head>, </body>)\n"
            f"   - Inclua a tag <style> com TODO o CSS dentro do body\n"
            f"   - NAO use blocos de codigo Markdown (```, ```html, etc)\n"
            f"   - Apenas codigo HTML/CSS puro, sem explicacoes\n\n"
            f"8. IMPORTANTE - NAO GERAR LOGO:\n"
            f"   - NAO inclua nenhuma secao de logo ou marca visual\n"
            f"   - NAO crie um elemento de logo no cabecalho\n"
            f"   - Foque apenas no titulo do e-commerce e menu de navegacao\n\n"
            f"Comece a gerar o codigo agora:"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        response_text = response.choices[0].message.content
        
        # LIMPEZA: Remover blocos de código Markdown
        cleaned_text = clean_markdown_code(response_text)
        
        return wrap_xml("CodeGeneratorAgent", cleaned_text, tag="generated_code")

# Instâncias dos agentes
text_agent = TextGeneratorAgent()
ux_research_agent = UXResearchAgent()
ux_design_agent = UXDesignerAgent()
business_agent = BusinessAgent()
photographer_agent = PhotographerAgent()
spec_agent = SpecificationAgent()
code_agent = CodeGeneratorAgent()

# Para facilitar a importação dos helpers
__all__ = [
    "text_agent",
    "ux_research_agent",
    "ux_design_agent",
    "business_agent",
    "photographer_agent",
    "spec_agent",
    "code_agent",
    "extract_tag_content",
    "extract_products",
    "extract_images"
]