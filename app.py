# Importa as bibliotecas necessárias do Flask e os agentes de chat
from flask import Flask, request, render_template
from chat_agents import (
    text_agent,
    ux_research_agent,
    ux_design_agent,
    business_agent,
    photographer_agent,
    spec_agent,
    code_agent,
    extract_tag_content
)

# Cria uma instância do Flask
# Configura o Flask para servir arquivos estáticos do diretório 'static'
app = Flask(__name__, template_folder='templates', static_folder='static')

# Define a rota principal da aplicação, que aceita métodos GET e POST
@app.route("/", methods=["GET", "POST"])
def index():
    # Verifica se o método da requisição é POST
    if request.method == "POST":
        # Obtém o valor do campo 'product' do formulário
        product = request.form.get("product")
        if product:
            try:
                print(f"\n🚀 Iniciando geração de e-commerce para: {product}")
                
                # Fluxo dos agentes usando XML para troca de dados
                print("\n📝 Etapa 1: Gerando contexto do produto...")
                context_xml = text_agent.respond(product)
                
                print("\n👥 Etapa 2: Criando persona do cliente...")
                persona_xml = ux_research_agent.respond(context_xml)
                
                print("\n🎨 Etapa 3: Definindo elementos de UX...")
                ux_elements_xml = ux_design_agent.respond(persona_xml)
                
                print("\n🛒 Etapa 4: Criando lista de produtos (Máx 3)...")
                products_xml = business_agent.respond(persona_xml)
                
                print("\n🖼️ Etapa 5: Gerando e SALVANDO imagens dos produtos (Máx 3)...")
                images_xml = photographer_agent.respond(products_xml)
                
                print("\n📜 Etapa 6: Criando especificação técnica...")
                specification_xml = spec_agent.respond(persona_xml, ux_elements_xml, images_xml)
                
                print("\n💻 Etapa 7: Gerando código HTML/CSS (Sem blocos Markdown)...")
                generated_code_xml = code_agent.respond(specification_xml, images_xml, products_xml)
                
                # Extrai o código gerado do XML
                code_output = extract_tag_content(generated_code_xml, tag="generated_code")
                
                print("\n✅ E-commerce gerado com sucesso!")
                print("\n🌐 Renderizando no navegador...")
                
                # Renderiza o template com o código gerado
                return render_template('base.html', generated_content=code_output)
            
            except Exception as e:
                print(f"\n❌ Erro durante a geração: {str(e)}")
                return f"""
                <!DOCTYPE html>
                <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Erro na Geração</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 50px; }}
                            .error {{ color: red; padding: 20px; border: 1px solid red; border-radius: 5px; }}
                        </style>
                    </head>
                    <body>
                        <div class="error">
                            <h1>❌ Erro na Geração do E-commerce</h1>
                            <p><strong>Detalhes:</strong> {str(e)}</p>
                            <p><a href="/">Voltar</a></p>
                        </div>
                    </body>
                </html>
                """
    
    # Retorna o formulário HTML para o método GET (mantido do app_novo.py)
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Gerador de E-commerce com Multiagentes e IA</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 20px;
                }
                
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                    max-width: 500px;
                    width: 100%;
                }
                
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                    font-size: 28px;
                }
                
                .subtitle {
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 14px;
                }
                
                label {
                    display: block;
                    margin-bottom: 8px;
                    color: #333;
                    font-weight: 500;
                }
                
                input[type="text"] {
                    width: 100%;
                    padding: 12px;
                    margin-bottom: 20px;
                    border: 2px solid #e0e0e0;
                    border-radius: 5px;
                    font-size: 16px;
                    transition: border-color 0.3s;
                }
                
                input[type="text"]:focus {
                    outline: none;
                    border-color: #667eea;
                }
                
                input[type="submit"] {
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                
                input[type="submit"]:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                }
                
                input[type="submit"]:active {
                    transform: translateY(0);
                }
                
                .info {
                    margin-top: 20px;
                    padding: 15px;
                    background: #f5f5f5;
                    border-radius: 5px;
                    font-size: 13px;
                    color: #666;
                    line-height: 1.6;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛍️ Gerador de E-commerce</h1>
                <p class="subtitle">Crie um e-commerce único com IA multiagente</p>
                <form method="post">
                    <label for="product">Digite um produto para vender:</label>
                    <input type="text" id="product" name="product" placeholder="Ex: Fones de ouvido wireless" required autofocus>
                    <input type="submit" value="Gerar E-commerce">
                </form>
                <div class="info">
                    <strong>💡 Como funciona:</strong><br>
                    1. Digite o nome de um produto<br>
                    2. Nossos agentes de IA analisam e criam uma persona<br>
                    3. Um e-commerce personalizado é gerado<br>
                    4. Você vê o resultado em tempo real
                </div>
            </div>
        </body>
    </html>
    """

# Executa a aplicação Flask no modo debug
if __name__ == "__main__":
    app.run(debug=True)