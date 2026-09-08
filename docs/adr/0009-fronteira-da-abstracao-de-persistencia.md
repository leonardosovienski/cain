# ADR-0009 — Fronteira da abstração de persistência

- **Status:** Aceito
- **Faixa:** A (engenharia)
- **Data:** 2026-09-07
- **Relacionados:** ADR-0002 (desacoplar de LLM específico), ADR-0005 (fronteira da abstração de LLM), ADR-0006 (modelo de dados da identidade), ADR-0010 (protocolo de avaliação)

> Adaptar ao template de `docs/adr/` antes de commitar.

---

## Contexto

A camada de Identidade precisa que o estado da persona sobreviva ao fim da sessão — é literalmente
o que a palavra "persistente" no título do trabalho significa. Sem persistência, não há artefato.

O projeto já declarou o caminho de escalonamento: SQLite + ChromaDB na fase de TCC, PostgreSQL +
banco vetorial gerenciado em escala. Mas essa decisão estava registrada como item de stack, não como
fronteira arquitetural. Isso produziu uma assimetria sem justificativa: a fronteira do LLM tem ADR
próprio (0005) e nenhuma camada conhece o provedor concreto, enquanto o armazenamento ficaria livre
para vazar `sqlite3` ou `chromadb` para dentro do serviço de identidade.

Se isso acontecer, três coisas quebram de uma vez:

1. A troca SQLite → PostgreSQL vira refatoração, contrariando a diretriz de escalonamento sem
   refatoração do núcleo (§2 do documento mestre).
2. Testes unitários da camada de identidade passam a exigir banco real.
3. A promessa de reprodutibilidade da avaliação fica dependente de um estado de banco opaco.

## Decisão

Definir a persistência como **três portas separadas**, não uma abstração genérica de armazenamento:

| Porta | Responsabilidade | Natureza do dado |
|---|---|---|
| `IdentityStore` | Estado da persona por usuário | Autoritativo, mutável, transacional |
| `MemoryIndex` | Recuperação semântica de interações passadas | **Derivado, reconstruível**, aproximado |
| `DecisionLog` | Registro de decisões do orquestrador | Append-only, imutável, dado de pesquisa |

Nenhuma camada acima conhece o backend concreto. Os adaptadores vivem em
`src/cain/persistence/adapters/`.

### Contratos

```python
class IdentityStore(Protocol):
    def get(self, user_id: str) -> IdentityState | None: ...
    def upsert(self, user_id: str, state: IdentityState) -> None: ...
    def append_signal(self, user_id: str, signal: Signal) -> None: ...
    def history(self, user_id: str, limit: int) -> list[IdentitySnapshot]: ...

class MemoryIndex(Protocol):
    def index(self, doc_id: str, text: str, metadata: dict) -> None: ...
    def query(self, text: str, k: int, filters: dict | None) -> list[Hit]: ...
    def rebuild_from(self, source: IdentityStore) -> None: ...
    def drop(self) -> None: ...

class DecisionLog(Protocol):
    def append(self, record: DecisionRecord) -> None: ...
    def export(self, run_id: str) -> Iterable[DecisionRecord]: ...
```

### Invariante central

> **O `MemoryIndex` é sempre reconstruível a partir do `IdentityStore`.**

O índice vetorial nunca é fonte da verdade. Perder o ChromaDB inteiro não pode perder nenhum dado —
só custa um `rebuild_from`.

## Justificativa

**Por que três portas e não uma.** Os três dados têm requisitos de consistência e modos de falha
incompatíveis. Um único `Storage.get/set` genérico forçaria o índice vetorial a fingir que é
autoritativo, que é exatamente o erro que se paga caro depois. Separar torna explícito o que é
verdade, o que é cache e o que é evidência.

**Por que o `DecisionLog` é porta própria e não uma tabela qualquer.** Ele não é estado de aplicação
— é o dado bruto da avaliação. Precisa ser append-only (um registro nunca é corrigido depois de
escrito), exportável para análise e versionável junto dos resultados. Misturá-lo ao estado mutável da
identidade abriria a porta para um log ser alterado depois da coleta, o que compromete a integridade
do experimento. Colocar isso na arquitetura é mais barato que confiar na disciplina do autor às duas
da manhã.

**Por que a invariante de reconstrução importa além da engenharia.** Ela transforma a migração
ChromaDB → banco gerenciado em *rebuild*, não em migração de dados. E dá à avaliação uma propriedade
forte: um terceiro consegue reconstruir o estado semântico a partir dos dados relacionais versionados,
sem precisar do meu índice. Isso atende diretamente à diretriz 3 de Hevner (avaliação do design) e é
argumento de reprodutibilidade para a qualificação.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
|---|---|
| Porta única genérica de storage | Achata três semânticas diferentes; obriga o índice vetorial a se passar por autoritativo |
| ORM (SQLAlchemy) direto no serviço de identidade | Acopla a camada de pesquisa a um detalhe de infraestrutura; contraria ADR-0002 por analogia |
| Sem abstração até precisar (YAGNI) | A necessidade já é conhecida e datada: o caminho de escalonamento está declarado desde o esboço. YAGNI se aplica a requisitos hipotéticos, não a requisitos adiados |
| Repositório único com dois backends internos | Esconde a distinção autoritativo/derivado dentro da implementação, onde ela não pode ser testada |

## Consequências

**Positivas**
- Troca de backend por configuração; nenhuma camada superior é tocada.
- Testes da camada de identidade rodam com dublês em memória, sem banco.
- Estado da avaliação reconstruível por terceiros.
- O log de decisões fica protegido de mutação por design, não por convenção.

**Negativas**
- Três interfaces e adaptadores para um protótipo de três agentes: parece
  sobre-engenharia, e um avaliador pode dizer isso. A resposta é a invariante de reconstrução
  e a integridade do log — ambas são requisito de pesquisa, não capricho de arquitetura.
- Custo inicial de ~1 dia de implementação antes de qualquer funcionalidade visível.

**Riscos**
- Se o `MemoryIndex` acumular estado que não existe no `IdentityStore`, a invariante quebra em
  silêncio. **Mitigação:** teste de integração que faz `drop()` + `rebuild_from()` e compara os
  resultados de um conjunto fixo de consultas antes e depois. Esse teste é a guarda da invariante e
  deve existir desde a primeira versão.
