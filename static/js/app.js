let livros = [];
let usuarios = [];
let logs = [];
let backups = [];

document.addEventListener("DOMContentLoaded", async () => {
  await carregarLivrosDoBanco();
  await carregarUsuariosDoBanco();
  await carregarLogsDoBanco();
  await carregarBackups();

  lucide.createIcons();
});

function alternarDarkMode() {
  const html = document.documentElement;
  const icone = document.getElementById("iconeTema");

  if (html.classList.contains("dark")) {
    html.classList.remove("dark");
    html.classList.add("light");

    if (icone) {
      icone.setAttribute("data-lucide", "moon");
    }
  } else {
    html.classList.remove("light");
    html.classList.add("dark");

    if (icone) {
      icone.setAttribute("data-lucide", "sun");
    }
  }

  lucide.createIcons();
}

async function carregarLivrosDoBanco() {
  try {
    const res = await fetch("/api/livros");

    if (!res.ok) {
      throw new Error("Não foi possível carregar os livros.");
    }

    const dados = await res.json();

    livros = dados.map(l => ({
      ...l,
      id: l.id ?? l.id_livro,
      disponivel: l.disponivel ?? l.quantidade_disponivel
    }));

    renderizarCatalogo(livros);
    renderizarDisponiveis(livros);
    atualizarSelectsTransacoes();
    atualizarResumo();

  } catch (e) {
    console.error("Erro ao carregar livros:", e);
  }
}

async function carregarUsuariosDoBanco() {
  try {
    const res = await fetch("/api/usuarios");

    if (!res.ok) {
      throw new Error("Não foi possível carregar os usuários.");
    }

    const dados = await res.json();

    usuarios = dados.map(u => ({
      ...u,
      id: u.id ?? u.id_usuario
    }));

    renderizarUsuarios(usuarios);
    atualizarSelectsTransacoes();
    atualizarResumo();

  } catch (e) {
    console.error("Erro ao carregar usuários:", e);
  }
}

async function carregarLogsDoBanco() {
  try {
    const res = await fetch("/api/logs");

    if (!res.ok) {
      throw new Error("Não foi possível carregar os logs.");
    }

    logs = await res.json();

    renderizarLogs();
    atualizarResumo();

  } catch (e) {
    console.error("Erro ao carregar logs:", e);
  }
}

async function carregarBackups() {
  const container = document.getElementById("listaBackups");

  if (container) {
    container.innerHTML = `
      <div class="backup-loading">
        Carregando backups...
      </div>
    `;
  }

  try {
    const res = await fetch("/api/backups");

    if (!res.ok) {
      throw new Error("Não foi possível carregar os backups.");
    }

    backups = await res.json();

    renderizarBackups();

  } catch (e) {
    console.error("Erro ao carregar backups:", e);

    if (container) {
      container.innerHTML = `
        <div class="backup-empty">
          Não foi possível carregar os backups.
        </div>
      `;
    }
  }
}

function renderizarCatalogo(lista) {
  const grid = document.getElementById("gridCatalogo");

  if (!grid) {
    return;
  }

  grid.innerHTML = "";

  if (lista.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <strong>Nenhum livro encontrado.</strong>
        <span>Não há livros correspondentes à busca.</span>
      </div>
    `;

    return;
  }

  lista.forEach(l => {
    const disp = Number(l.disponivel) > 0;

    const capa =
      l.capa_url ||
      "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&q=80";

    grid.innerHTML += `
      <article class="book-card ${disp ? "" : "out"}">

        <div class="book-cover-wrap">

          <img
            src="${capa}"
            alt="${l.titulo}"
            class="book-cover"
          >

          <span class="book-id">
            ID #${l.id}
          </span>

          <button
            onclick="apagarLivro(${l.id})"
            class="delete-book"
            title="Apagar livro"
          >
            <i data-lucide="trash-2"></i>
          </button>

        </div>

        <div class="book-info">

          <span class="status ${disp ? "available" : "empty"}">
            ${disp ? `${l.disponivel} disponíveis` : "Esgotado"}
          </span>

          <h3>${l.titulo}</h3>

          <p>Autor: ${l.autor}</p>

          <button
            class="book-action"
            onclick="irParaEmprestimoComLivro(${l.id})"
            ${disp ? "" : "disabled"}
          >
            ${disp ? "Realizar empréstimo" : "Indisponível"}
          </button>

        </div>

      </article>
    `;
  });

  lucide.createIcons();
}

function filtrarCatalogo() {
  const campo = document.getElementById("campoBuscaCatalogo");

  if (!campo) {
    return;
  }

  const termo = campo.value.toLowerCase().trim();

  const filtrados = livros.filter(l =>
    String(l.titulo || "").toLowerCase().includes(termo) ||
    String(l.autor || "").toLowerCase().includes(termo) ||
    String(l.id || "").toLowerCase().includes(termo)
  );

  renderizarCatalogo(filtrados);
}

function renderizarDisponiveis(lista) {
  const grid = document.getElementById("gridDisponiveis");

  if (!grid) {
    return;
  }

  grid.innerHTML = "";

  const disponiveis = lista.filter(
    l => Number(l.disponivel) > 0
  );

  if (disponiveis.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <strong>Nenhum livro disponível.</strong>
        <span>Nenhum exemplar está disponível para empréstimo.</span>
      </div>
    `;

    return;
  }

  disponiveis.forEach(l => {
    const capa =
      l.capa_url ||
      "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&q=80";

    grid.innerHTML += `
      <article class="book-card">

        <div class="book-cover-wrap">

          <img
            src="${capa}"
            alt="${l.titulo}"
            class="book-cover"
          >

          <span class="book-id">
            ID #${l.id}
          </span>

        </div>

        <div class="book-info">

          <span class="status available">
            ${l.disponivel} disponíveis
          </span>

          <h3>${l.titulo}</h3>

          <p>Autor: ${l.autor}</p>

          <button
            class="book-action"
            onclick="irParaEmprestimoComLivro(${l.id})"
          >
            Realizar empréstimo
          </button>

        </div>

      </article>
    `;
  });

  lucide.createIcons();
}

function filtrarDisponiveis() {
  const campo = document.getElementById("campoBuscaDisponiveis");

  if (!campo) {
    return;
  }

  const termo = campo.value.toLowerCase().trim();

  const filtrados = livros.filter(l =>
    Number(l.disponivel) > 0 &&
    (
      String(l.titulo || "").toLowerCase().includes(termo) ||
      String(l.autor || "").toLowerCase().includes(termo) ||
      String(l.id || "").includes(termo)
    )
  );

  renderizarDisponiveis(filtrados);
}

function renderizarUsuarios(lista) {
  const tabela = document.getElementById("tabelaUsuarios");

  if (!tabela) {
    return;
  }

  tabela.innerHTML = "";

  if (lista.length === 0) {
    tabela.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;">
          Nenhum leitor encontrado.
        </td>
      </tr>
    `;

    return;
  }

  lista.forEach(u => {
    tabela.innerHTML += `
      <tr>

        <td class="table-id">
          #${u.id}
        </td>

        <td>
          <strong>${u.nome}</strong>
        </td>

        <td>
          ${u.cpf || "-"}
        </td>

        <td>
          ${u.email}
        </td>

        <td>
          ${u.telefone || "-"}
        </td>

      </tr>
    `;
  });
}

function filtrarUsuarios() {
  const campo = document.getElementById("buscaUsuarioInput");

  if (!campo) {
    return;
  }

  const termo = campo.value.toLowerCase().trim();

  const filtrados = usuarios.filter(u =>
    String(u.nome || "").toLowerCase().includes(termo) ||
    String(u.cpf || "").toLowerCase().includes(termo)
  );

  renderizarUsuarios(filtrados);
}

function atualizarSelectsTransacoes() {
  filtrarLeitoresEmp();
  filtrarLeitoresDev();

  const selectLivroEmp =
    document.getElementById("selectLivroEmp");

  if (!selectLivroEmp) {
    return;
  }

  selectLivroEmp.innerHTML = "";

  const disponiveis = livros.filter(
    l => Number(l.disponivel) > 0
  );

  if (disponiveis.length === 0) {
    selectLivroEmp.innerHTML = `
      <option value="">
        Nenhum livro disponível
      </option>
    `;

    return;
  }

  disponiveis.forEach(l => {
    selectLivroEmp.innerHTML += `
      <option value="${l.id}">
        ${l.titulo} (${l.disponivel} disp.)
      </option>
    `;
  });
}

function filtrarLeitoresEmp() {
  const campo = document.getElementById("buscaLeitorEmp");
  const select = document.getElementById("selectLeitorEmp");

  if (!campo || !select) {
    return;
  }

  const termo = campo.value.toLowerCase().trim();

  const filtrados = usuarios.filter(u =>
    String(u.nome || "").toLowerCase().includes(termo) ||
    String(u.cpf || "").toLowerCase().includes(termo)
  );

  select.innerHTML = "";

  if (filtrados.length === 0) {
    select.innerHTML = `
      <option value="">
        Nenhum leitor encontrado
      </option>
    `;

    return;
  }

  filtrados.forEach(u => {
    select.innerHTML += `
      <option value="${u.id}">
        ${u.nome} - CPF: ${u.cpf || "não informado"}
      </option>
    `;
  });
}

function filtrarLeitoresDev() {
  const campo = document.getElementById("buscaLeitorDev");
  const select = document.getElementById("selectLeitorDev");

  if (!campo || !select) {
    return;
  }

  const termo = campo.value.toLowerCase().trim();

  const filtrados = usuarios.filter(u =>
    String(u.nome || "").toLowerCase().includes(termo) ||
    String(u.cpf || "").toLowerCase().includes(termo)
  );

  select.innerHTML = "";

  if (filtrados.length === 0) {
    select.innerHTML = `
      <option value="">
        Nenhum leitor encontrado
      </option>
    `;

    return;
  }

  filtrados.forEach(u => {
    select.innerHTML += `
      <option value="${u.id}">
        ${u.nome} - CPF: ${u.cpf || "não informado"}
      </option>
    `;
  });

  carregarLivrosPendentesLeitor();
}

async function carregarLivrosPendentesLeitor() {
  const selectUsuario =
    document.getElementById("selectLeitorDev");

  const selectLivro =
    document.getElementById("selectLivroDev");

  if (!selectUsuario || !selectLivro) {
    return;
  }

  const idUsuario = selectUsuario.value;

  selectLivro.innerHTML = "";

  if (!idUsuario) {
    selectLivro.innerHTML = `
      <option value="">
        Selecione um leitor acima primeiro...
      </option>
    `;

    return;
  }

  try {
    const res =
      await fetch(`/api/emprestimos/usuario/${idUsuario}`);

    if (!res.ok) {
      throw new Error("Não foi possível carregar os empréstimos.");
    }

    const pendentes = await res.json();

    if (pendentes.length === 0) {
      selectLivro.innerHTML = `
        <option value="">
          Nenhum livro pendente para este leitor.
        </option>
      `;

      return;
    }

    pendentes.forEach(p => {
      selectLivro.innerHTML += `
        <option
          value="${p.id_livro}"
          data-emprestimo="${p.id_emprestimo}"
        >
          [Emp #${p.id_emprestimo}]
          ${p.titulo}
          (Limite: ${p.data_prevista})
        </option>
      `;
    });

  } catch (e) {
    console.error(
      "Erro ao buscar empréstimos pendentes:",
      e
    );

    selectLivro.innerHTML = `
      <option value="">
        Erro ao carregar empréstimos.
      </option>
    `;
  }
}

async function efetuarEmprestimoLeitor() {
  const selectUsuario =
    document.getElementById("selectLeitorEmp");

  const selectLivro =
    document.getElementById("selectLivroEmp");

  const idUsuario = parseInt(selectUsuario?.value);
  const idLivro = parseInt(selectLivro?.value);

  if (!idUsuario || !idLivro) {
    alert("Selecione um leitor e um livro válidos.");
    return;
  }

  try {
    const res = await fetch("/api/emprestimos", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        id_usuario: idUsuario,
        id_livro: idLivro
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Erro ao realizar empréstimo."
      );
    }

    alert(
      `Empréstimo registrado com sucesso!\n\nPrazo de devolução: ${data.devolucao_prevista}`
    );

    await carregarLivrosDoBanco();
    await carregarLogsDoBanco();

  } catch (e) {
    alert("Erro: " + e.message);
  }
}

async function efetuarDevolucaoLeitor() {
  const selectUsuario =
    document.getElementById("selectLeitorDev");

  const selectLivro =
    document.getElementById("selectLivroDev");

  const idUsuario = parseInt(selectUsuario?.value);
  const idLivro = parseInt(selectLivro?.value);

  const opcao =
    selectLivro?.selectedOptions?.[0];

  const idEmprestimo =
    opcao?.dataset?.emprestimo
      ? parseInt(opcao.dataset.emprestimo)
      : null;

  if (!idUsuario || !idLivro) {
    alert(
      "Selecione o leitor e o livro pendente para devolução."
    );

    return;
  }

  try {
    const res = await fetch("/api/devolucoes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        id_usuario: idUsuario,
        id_livro: idLivro,
        id_emprestimo: idEmprestimo
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Erro ao realizar devolução."
      );
    }

    alert(
      "Devolução efetuada e estoque reposto com sucesso!"
    );

    await carregarLivrosDoBanco();
    await carregarLogsDoBanco();
    await carregarLivrosPendentesLeitor();

  } catch (e) {
    alert("Erro: " + e.message);
  }
}

async function apagarLivro(id) {
  if (!confirm("Deseja mesmo remover este livro?")) {
    return;
  }

  try {
    const res =
      await fetch(`/api/livros/${id}`, {
        method: "DELETE"
      });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Não foi possível excluir o livro."
      );
    }

    await carregarLivrosDoBanco();
    await carregarLogsDoBanco();

    alert("Livro removido com sucesso.");

  } catch (e) {
    alert("Erro: " + e.message);
  }
}

function irParaEmprestimoComLivro(idLivro) {
  alternarAba("transacoes");

  const select =
    document.getElementById("selectLivroEmp");

  if (select) {
    select.value = String(idLivro);
  }
}

function renderizarLogs() {
  const container =
    document.getElementById("containerLogs");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (logs.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        Nenhum evento registrado.
      </div>
    `;

    return;
  }

  logs.forEach(l => {
    container.innerHTML += `
      <div class="log-item">

        <div class="log-icon">
          <i data-lucide="activity"></i>
        </div>

        <div class="log-content">

          <div class="log-top">
            <span>${l.tipo_evento}</span>
            <span>${l.timestamp || ""}</span>
          </div>

          <p>${l.detalhes}</p>

        </div>

      </div>
    `;
  });

  lucide.createIcons();
}

function renderizarBackups() {
  const container =
    document.getElementById("listaBackups");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (backups.length === 0) {
    container.innerHTML = `
      <div class="backup-empty">
        Nenhum backup encontrado.
      </div>
    `;

    return;
  }

  backups.forEach(backup => {
    container.innerHTML += `
      <div class="backup-item">

        <div class="backup-info">

          <div class="backup-icon">
            <i data-lucide="database-backup"></i>
          </div>

          <div>

            <div class="backup-name">
              ${backup.arquivo}
            </div>

            <div class="backup-meta">
              ${backup.data}
              •
              ${formatarTamanho(backup.tamanho)}
            </div>

          </div>

        </div>

        <button
          class="restore-btn"
          onclick="restaurarBackup('${backup.arquivo}')"
        >

          <i data-lucide="rotate-ccw"></i>
          Restaurar

        </button>

      </div>
    `;
  });

  lucide.createIcons();
}

function formatarTamanho(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function criarBackup() {
  const botao =
    document.getElementById("btnCriarBackup");

  try {
    if (botao) {
      botao.disabled = true;

      botao.innerHTML = `
        <i data-lucide="loader-circle"></i>
        Criando backup...
      `;

      lucide.createIcons();
    }

    const res = await fetch("/api/backup", {
      method: "POST"
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Não foi possível criar o backup."
      );
    }

    alert(
      `Backup criado com sucesso!\n\nArquivo: ${data.arquivo}`
    );

    await carregarBackups();
    await carregarLogsDoBanco();

  } catch (e) {

    console.error("Erro ao criar backup:", e);

    alert(
      "Erro ao criar backup:\n\n" +
      e.message
    );

  } finally {

    if (botao) {
      botao.disabled = false;

      botao.innerHTML = `
        <i data-lucide="database-backup"></i>
        Criar backup agora
      `;

      lucide.createIcons();
    }
  }
}

async function restaurarBackup(nomeArquivo) {
  const confirmacao = confirm(
    "ATENÇÃO!\n\n" +
    "Você está prestes a restaurar o banco de dados para o estado deste backup:\n\n" +
    `${nomeArquivo}\n\n` +
    "Todas as alterações feitas depois desse backup serão substituídas.\n\n" +
    "Antes da restauração, o sistema criará automaticamente um backup de segurança do estado atual.\n\n" +
    "Deseja realmente continuar?"
  );

  if (!confirmacao) {
    return;
  }

  try {
    const res = await fetch("/api/backup/restaurar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        arquivo: nomeArquivo
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Não foi possível restaurar o backup."
      );
    }

    alert(
      "Backup restaurado com sucesso!\n\n" +
      `Backup restaurado: ${data.arquivo}\n\n` +
      `Backup de segurança criado automaticamente:\n${data.backup_seguranca}`
    );

    await carregarLivrosDoBanco();
    await carregarUsuariosDoBanco();
    await carregarLogsDoBanco();
    await carregarBackups();

    alternarAba("catalogo");

  } catch (e) {

    console.error("Erro ao restaurar backup:", e);

    alert(
      "Erro ao restaurar o backup:\n\n" +
      e.message
    );
  }
}

function atualizarResumo() {
  const el = (id, valor) => {
    const elemento =
      document.getElementById(id);

    if (elemento) {
      elemento.textContent = valor;
    }
  };

  el("statLivros", livros.length);

  el(
    "statDisponiveis",
    livros.reduce(
      (total, livro) =>
        total +
        Math.max(
          0,
          Number(livro.disponivel) || 0
        ),
      0
    )
  );

  el("statUsuarios", usuarios.length);
  el("statLogs", logs.length);
}

function alternarAba(aba) {
  const abas = [
    "catalogo",
    "disponiveis",
    "usuarios",
    "transacoes",
    "logs",
    "backups"
  ];

  abas.forEach(a => {
    const secao =
      document.getElementById(`sec-${a}`);

    const botao =
      document.getElementById(`tab-${a}`);

    if (secao) {
      secao.classList.add("hidden");
    }

    if (botao) {
      botao.classList.remove("active");
    }
  });

  const secaoAtiva =
    document.getElementById(`sec-${aba}`);

  const botaoAtivo =
    document.getElementById(`tab-${aba}`);

  if (secaoAtiva) {
    secaoAtiva.classList.remove("hidden");
  }

  if (botaoAtivo) {
    botaoAtivo.classList.add("active");
  }

  const titulos = {
    catalogo: "Catálogo geral",
    disponiveis: "Disponibilidade",
    usuarios: "Leitores",
    transacoes: "Movimentações",
    logs: "Auditoria",
    backups: "Backups"
  };

  const pageTitle =
    document.getElementById("pageTitle");

  if (pageTitle) {
    pageTitle.textContent =
      titulos[aba] || "Biblioteca";
  }

  if (aba === "backups") {
    carregarBackups();
  }
}

function abrirModalUsuario() {
  const modal =
    document.getElementById("modalUsuario");

  if (modal) {
    modal.classList.remove("hidden");
  }
}

function fecharModalUsuario() {
  const modal =
    document.getElementById("modalUsuario");

  if (modal) {
    modal.classList.add("hidden");
  }
}

function abrirModalLivro() {
  const modal =
    document.getElementById("modalLivro");

  if (modal) {
    modal.classList.remove("hidden");
  }
}

function fecharModalLivro() {
  const modal =
    document.getElementById("modalLivro");

  if (modal) {
    modal.classList.add("hidden");
  }
}

function aplicarMascaraCPF(input) {
  let valor =
    input.value.replace(/\D/g, "");

  valor = valor.substring(0, 11);

  valor = valor.replace(
    /(\d{3})(\d)/,
    "$1.$2"
  );

  valor = valor.replace(
    /(\d{3})(\d)/,
    "$1.$2"
  );

  valor = valor.replace(
    /(\d{3})(\d{1,2})$/,
    "$1-$2"
  );

  input.value = valor;
}

function aplicarMascaraTelefone(input) {
  let valor =
    input.value.replace(/\D/g, "");

  valor = valor.substring(0, 11);

  if (valor.length <= 10) {

    valor = valor.replace(
      /(\d{2})(\d)/,
      "($1) $2"
    );

    valor = valor.replace(
      /(\d{4})(\d)/,
      "$1-$2"
    );

  } else {

    valor = valor.replace(
      /(\d{2})(\d)/,
      "($1) $2"
    );

    valor = valor.replace(
      /(\d{5})(\d)/,
      "$1-$2"
    );
  }

  input.value = valor;
}

async function salvarLivro(event) {
  event.preventDefault();

  const titulo =
    document.getElementById("livroTitulo").value;

  const autor =
    document.getElementById("livroAutor").value;

  const isbn =
    document.getElementById("livroIsbn").value;

  const quantidade =
    parseInt(
      document.getElementById("livroQtd").value
    ) || 0;

  const capa =
    document.getElementById("livroCapa").value;

  try {
    const res = await fetch("/api/livros", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        titulo,
        autor,
        isbn,
        quantidade_disponivel: quantidade,
        capa_url: capa
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Erro ao cadastrar livro."
      );
    }

    fecharModalLivro();
    event.target.reset();

    await carregarLivrosDoBanco();
    await carregarLogsDoBanco();

    alert("Livro cadastrado com sucesso.");

  } catch (e) {
    alert("Erro: " + e.message);
  }
}

async function salvarUsuario(event) {
  event.preventDefault();

  const nome =
    document.getElementById("cadNome").value;

  const cpf =
    document.getElementById("cadCPF").value;

  const telefone =
    document.getElementById("cadTelefone").value;

  const email =
    document.getElementById("cadEmail").value;

  try {
    const res = await fetch("/api/usuarios", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        nome,
        cpf,
        telefone,
        email
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.erro || "Erro ao cadastrar leitor."
      );
    }

    fecharModalUsuario();
    event.target.reset();

    await carregarUsuariosDoBanco();
    await carregarLogsDoBanco();

    alert("Leitor cadastrado com sucesso.");

  } catch (e) {
    alert("Erro: " + e.message);
  }
}