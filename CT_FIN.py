import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
from github import Github

# Dicionário de usuários (temporário)
USERS = {
    "henrique.degan": "12345",
    "vanessa.degan": "12345"
}

# Função para verificar login
def authenticate(username, password):
    return USERS.get(username) == password

# Função para salvar dados no GitHub
def save_to_github(data, filename, repo_name, branch="main"):
    GITHUB_TOKEN = "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"  # Substitua pelo seu token de acesso pessoal
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    
    # Converte o DataFrame para CSV
    csv_data = data.to_csv(index=False)
    
    # Verifica se o arquivo já existe no repositório
    try:
        contents = repo.get_contents(filename, ref=branch)
        repo.update_file(contents.path, f"Atualizando {filename}", csv_data, contents.sha, branch=branch)
        st.success(f"Arquivo {filename} atualizado no GitHub!")
    except:
        repo.create_file(filename, f"Criando {filename}", csv_data, branch=branch)
        st.success(f"Arquivo {filename} criado no GitHub!")

# Função para carregar dados do GitHub
def load_from_github(filename, repo_name, branch="main"):
    GITHUB_TOKEN = "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"  # Substitua pelo seu token de acesso pessoal
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    
    try:
        contents = repo.get_contents(filename, ref=branch)
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(pd.compat.StringIO(csv_data))
    except Exception as e:
        st.warning(f"Erro ao carregar dados do GitHub: {e}")
        return pd.DataFrame(columns=[
            "Tipo", "Resumo", "Descrição", "Valor", "Data", "Categoria", "Contato", "Tag", "Obs", "Parcelas"
        ])

# Verificar se o usuário está logado
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# Inicializar dados de transações por usuário
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}

# Estado para controlar o formulário pop-up
if 'show_form' not in st.session_state:
    st.session_state.show_form = False
if 'form_type' not in st.session_state:
    st.session_state.form_type = None

# Listas de categorias e tags (pode ser expandida pelo usuário)
if 'categories' not in st.session_state:
    st.session_state.categories = {
        "Receita": ["Benefícios", "Salários", "Extras", "Outros"],
        "Despesa": ["Crédito", "Débitos", "Aluguel", "Outros"]
    }
if 'tags' not in st.session_state:
    st.session_state.tags = []

# Página de login
if not st.session_state.logged_in:
    st.title("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            # Inicializar DataFrame vazio para o usuário, se ainda não existir
            if username not in st.session_state.user_data:
                st.session_state.user_data[username] = load_from_github(f"{username}_transactions.csv", "seu_usuario/nome_do_repositorio")
            st.success(f"Bem-vindo, {username}!")
            st.experimental_rerun()  # Recarregar a página após o login
        else:
            st.error("Usuário ou senha inválidos.")
else:
    # Usuário logado, mostrar o aplicativo
    st.sidebar.write(f"Logado como: {st.session_state.username}")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.experimental_rerun()  # Recarregar a página após o logout

    # Menu para navegação
    menu = ["Início", "Adicionar Receita", "Adicionar Despesa", "Relatório Financeiro", "Visualizar Gráficos", "Anexos"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Início":
        st.subheader("Projeção Financeira")

        # Obter o DataFrame do usuário atual
        current_user_data = st.session_state.user_data.get(st.session_state.username, pd.DataFrame())
        
        if not current_user_data.empty:
            # Converter a coluna "Data" para datetime, se ainda não estiver
            current_user_data["Data"] = pd.to_datetime(current_user_data["Data"])

            # Solicitar ao usuário quantos meses deseja projetar
            num_months = st.number_input("Digite quantos meses deseja projetar:", min_value=1, value=6, step=1)

            # Gerar lista de meses projetados
            today = datetime.today()
            projected_months = [(today + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(num_months)]

            # Criar uma tabela vazia para armazenar as projeções
            projection_table = pd.DataFrame(index=["Receitas", "Despesas", "Saldo"], columns=projected_months)

            # Preencher a tabela com receitas e despesas fixas e parceladas
            for month in projected_months:
                total_receitas, total_despesas = 0, 0

                for _, row in current_user_data.iterrows():
                    tipo = row["Tipo"]
                    valor = row["Valor"]
                    categoria = row["Categoria"]
                    parcelas = row["Parcelas"]
                    data = row["Data"]

                    # Calcular o mês da transação
                    transaction_month = data.strftime("%Y-%m")

                    # Se for fixo, adicionar em todos os meses
                    if categoria == "Fixo":
                        if tipo == "Receita":
                            total_receitas += valor
                        elif tipo == "Despesa":
                            total_despesas += valor

                    # Se for parcelado, distribuir nas parcelas
                    elif categoria == "Parcelado" and parcelas is not None:
                        for i in range(parcelas):
                            parcel_month = (data + timedelta(days=30 * i)).strftime("%Y-%m")
                            if parcel_month == month:
                                if tipo == "Receita":
                                    total_receitas += valor / parcelas
                                elif tipo == "Despesa":
                                    total_despesas += valor / parcelas

                # Calcular o saldo
                saldo = total_receitas - total_despesas

                # Preencher a tabela de projeção
                projection_table.loc["Receitas", month] = total_receitas
                projection_table.loc["Despesas", month] = total_despesas
                projection_table.loc["Saldo", month] = saldo

            # Adicionar coluna de acumulado geral
            projection_table["Acumulado"] = projection_table.sum(axis=1)

            # Exibir a tabela de projeção
            st.dataframe(projection_table.fillna(0))

        else:
            st.warning("Nenhuma transação registrada ainda.")

    elif choice in ["Adicionar Receita", "Adicionar Despesa"]:
        # Botão para abrir o formulário
        if not st.session_state.show_form:
            st.subheader("Transações Atuais")
            current_user_data = st.session_state.user_data.get(st.session_state.username, pd.DataFrame())
            st.dataframe(current_user_data)

            if st.button(f"Abrir Formulário para {choice}"):
                st.session_state.show_form = True
                st.session_state.form_type = choice
                st.experimental_rerun()

        # Exibir o formulário pop-up
        if st.session_state.show_form:
            st.subheader(f"{st.session_state.form_type}")

            current_user_data = st.session_state.user_data.get(st.session_state.username, pd.DataFrame())

            # Botões para adicionar nova categoria e tag (fora do formulário)
            if st.button("Adicionar Nova Categoria"):
                new_category = st.text_input("Digite o nome da nova categoria")
                if new_category:
                    st.session_state.categories[st.session_state.form_type.split()[-1]].append(new_category)
                    st.success(f"Categoria '{new_category}' adicionada com sucesso!")
                    st.experimental_rerun()

            if st.button("Adicionar Nova Tag"):
                new_tag = st.text_input("Digite o nome da nova tag")
                if new_tag:
                    st.session_state.tags.append(new_tag)
                    st.success(f"Tag '{new_tag}' adicionada com sucesso!")
                    st.experimental_rerun()

            # Formulário principal
            with st.form(key='transaction_form'):
                resumo = st.text_input("Resumo")
                descricao = st.text_input("Descrição")
                valor = st.number_input("Valor", min_value=0.0, format="%.2f")
                data = st.date_input("Data")
                categoria = st.selectbox("Categoria", st.session_state.categories[st.session_state.form_type.split()[-1]])
                contato = st.selectbox("Contato", ["Vanessa Degan", "Henrique Degan"])
                tag = st.selectbox("Tag", st.session_state.tags)
                obs = st.text_area("Observação")
                parcelas = None
                if st.checkbox("Parcelado"):
                    parcelas = st.number_input("Número de Parcelas", min_value=1, value=1, step=1)
                    
                submit_button = st.form_submit_button(label='Adicionar')

                if submit_button:
                    tipo = "Receita" if st.session_state.form_type == "Adicionar Receita" else "Despesa"
                    new_transaction = pd.DataFrame({
                        "Tipo": [tipo],
                        "Resumo": [resumo],
                        "Descrição": [descricao],
                        "Valor": [valor],
                        "Data": [data],
                        "Categoria": [categoria],
                        "Contato": [contato],
                        "Tag": [tag],
                        "Obs": [obs],
                        "Parcelas": [parcelas]
                    })
                    st.session_state.user_data[st.session_state.username] = pd.concat(
                        [current_user_data, new_transaction], ignore_index=True
                    )
                    save_to_github(st.session_state.user_data[st.session_state.username], f"{st.session_state.username}_transactions.csv", "seu_usuario/nome_do_repositorio")
                    st.success(f"{tipo} adicionada com sucesso!")
                    st.session_state.show_form = False
                    st.experimental_rerun()

            # Botão para fechar o formulário
            if st.button("Fechar Formulário"):
                st.session_state.show_form = False
                st.experimental_rerun()

    elif choice == "Relatório Financeiro":
        st.subheader("Relatório Financeiro")

        # Obter o DataFrame do usuário atual
        current_user_data = st.session_state.user_data.get(st.session_state.username, pd.DataFrame())

        if not current_user_data.empty:
            # Calcular totais de receitas e despesas
            total_receitas = current_user_data[current_user_data["Tipo"] == "Receita"]["Valor"].sum()
            total_despesas = current_user_data[current_user_data["Tipo"] == "Despesa"]["Valor"].sum()
            saldo_liquido = total_receitas - total_despesas

            # Exibir os totais
            st.metric("Total de Receitas", f"R$ {total_receitas:.2f}")
            st.metric("Total de Despesas", f"R$ {total_despesas:.2f}")
            st.metric("Saldo Líquido", f"R$ {saldo_liquido:.2f}")

            # Criar um gráfico de barras para comparar receitas e despesas
            summary = pd.DataFrame({
                "Categoria": ["Receitas", "Despesas"],
                "Valor": [total_receitas, total_despesas]
            })

            fig = px.bar(summary, x="Categoria", y="Valor", title="Receitas vs Despesas", color="Categoria")
            st.plotly_chart(fig)
        else:
            st.warning("Nenhuma transação registrada ainda.")

    elif choice == "Visualizar Gráficos":
        st.write("Aqui você verá gráficos das suas finanças.")
        # Implementaremos isso depois.

    elif choice == "Anexos":
        st.write("Aqui você pode gerenciar seus anexos.")
        # Implementaremos isso depois.
