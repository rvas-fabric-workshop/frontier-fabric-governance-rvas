# Runbook di erogazione — Frontier Fabric Governance Workshop
### Configurazioni e modifiche NON presenti sul sito GitHub del workshop

Repo di riferimento (upstream): `microsoft/frontier-fabric-governance-rvas`
Fork usato in questa erogazione: `rvas-fabric-workshop/frontier-fabric-governance-rvas`

> Scopo: raccogliere tutti i passaggi manuali, i workaround e le modifiche al repo
> scoperti durante l'erogazione, che **non sono documentati** (o sono documentati in
> modo ambiguo/errato) nel materiale ufficiale. Da usare come checklist per i Clienti.
> I primi prompt (creazione del semantic model per un altro Cliente) sono esclusi.

---

## 0. Valori/identità da preparare per ogni Cliente (segnaposto da sostituire)

| Variabile | Valore in questa erogazione | Note |
|---|---|---|
| GitHub org | `rvas-fabric-workshop` (ID `335498865`) | va creata nuova (le org aziendali SAML non vanno) |
| GitHub repo (fork) | `frontier-fabric-governance-rvas` (ID `1394977507`) | **pubblico** (vedi §2.7) |
| `AZURE_TENANT_ID` | `5f943b64-c792-41b3-90de-4f3443a387e7` | tenant Contoso/Fabric |
| `AZURE_CLIENT_ID` (appId) | `d0722f76-78b2-405b-8481-fbcf4582e408` | **client ID**, non l'object ID |
| App Registration object ID | `b222d59a-e5b5-4677-9207-32e416ad3465` | errore comune: usato per sbaglio come client ID |
| SPN (enterprise app) object ID | `21040b06-3d1f-4659-b736-b25116e8314b` | usare per Fabric Admin / Capacity Admin |
| `SECURITY_GROUP_ID` | `372ef100-5498-430a-b8ce-69241f8f73ce` | gruppo `sg-fabric-workspace-provisioner` |
| `FABRIC_CAPACITY_ID` (GUID) | `7fcfa848-36f2-4334-9225-c9a629a7e1e7` | capacity `democapacity1`, **Central US**, F16 |
| `DEFAULT_OWNER_UPN` | `stdetoni@MngEnvMCAP195373.onmicrosoft.com` | |
| `LIVE_CHECKS` | `true` | |
| Subscription | `63935975-6189-4de2-9a5c-8e63dfa8bd0f` | |

---

## 1. Tre identità distinte (chiarimento concettuale, spesso confuso)

1. **GitHub `sdt-msft`** — serve solo per licenza Copilot + operazioni git/PR. Non ha accesso ad AAD/Fabric.
2. **`az` CLI** — loggato sul tenant **Contoso** `5f943b64…` (utente `stdetoni@MngEnvMCAP195373.onmicrosoft.com`).
3. **MCP Fabric** — inizialmente autenticato con `stdetoni@microsoft.com` (tenant corporate, SBAGLIATO); va riautenticato sul tenant Contoso.

La licenza Copilot è **per-utente** e indipendente da org/tenant: non servono licenze extra.

---

## 2. CHALLENGE 0 — Setup (passaggi manuali e workaround non sul sito)

### 2.1 Org GitHub + fork
- Le org aziendali (microsoft, Azure, …) sono **SAML-protette** e l'utente vi è solo `member` → **creare una nuova org** dedicata.
- I fork/repo si creano di default nel namespace personale; per il workshop conviene la nuova org.

### 2.2 App Registration + Federated Credentials (OIDC, niente secret)
- 3 federated credentials sul App Registration (issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`), subject:
  - `…:pull_request`
  - `…:ref:refs/heads/main`
  - `…:environment:production`
- **PUNTO CRITICO non ovvio — subject "immutabili":** per i repo creati dopo il **15 luglio 2026** (questo fork rientra), la UI Entra richiede **Organization ID** e **Repository ID numerici**. Formato:
  ```
  repo:rvas-fabric-workshop@335498865/frontier-fabric-governance-rvas@1394977507:<subject>
  ```
  Recuperare gli ID con `gh api orgs/<org>` e `gh api repos/<org>/<repo>` (campo `id`).
- **Errore comune:** copiare l'**object ID** dell'App Registration al posto del **client ID (appId)**. Sono diversi.

### 2.3 Gruppo di sicurezza + ruoli Fabric
- Gruppo `sg-fabric-workspace-provisioner` con lo SPN come membro.
- Assegnare **Fabric Administrator** allo SPN (Entra → Roles).
- **Capacity Admin:** aggiungere lo SPN come admin sulla capacity (`democapacity1`).

### 2.4 Variabili Actions — TRAPPOLA di precedenza (non documentata)
- Le variabili possono stare a livello **org** o **repo**. **Repo-level sovrascrive org-level** con lo stesso nome.
- In questa erogazione era rimasta una `AZURE_TENANT_ID=none` a livello repo che **oscurava** il valore org corretto → login OIDC fallito finché non è stata **cancellata**.
- Set finale (repo-level) verificato:
  `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `DEFAULT_OWNER_UPN`, `FABRIC_CAPACITY_ID`, `LIVE_CHECKS=true`.

### 2.5 Environment `production`
- Creare l'environment `production` con **required reviewers** (gate di approvazione manuale usato da `provision.yml`).

### 2.6 CODEOWNERS — paradosso di bootstrap (non documentato)
- Il **primo** PR che aggiunge `.github/CODEOWNERS` non può soddisfare la ruleset `protect-main` (nessun code owner esiste ancora + non si può auto-approvare).
- **Fix:** in Settings → Rules → Rulesets → `protect-main` → **Bypass list** → aggiungere "Repository admin". Poi mergiare con privilegi admin.

### 2.7 Piani GitHub e repo pubblici (motivo della scelta)
- Branch protection via CODEOWNERS su repo **privato** richiede Team+; environment protection su privato richiede Enterprise.
- Su repo **pubblici** entrambe sono **gratis** → usare repo pubblici + piano Free.
- Gli OIDC non hanno secret, quindi il repo pubblico non espone credenziali.

### 2.8 MCP — configurazione e verifica (app, CLI, VS Code)
- **App desktop e Copilot CLI condividono** `~/.copilot/mcp-config.json` → già unificati.
- **VS Code è separato:** `%APPDATA%\Code\User\mcp.json` (globale) + `.vscode\mcp.json` (workspace). Non legge `~/.copilot/`.
- **Plugin vs MCP server:** un *plugin* (`fabric-skills`) è un bundle versionato che include skill + agent + **più** MCP server. VS Code non ha "plugin": l'analogo è l'**estensione** (può contribuire solo MCP server, non skill/agent).
- **Task 5 (Fabric Core MCP, remoto):** aggiungere server HTTP `https://api.fabric.microsoft.com/v1/mcp/core` (nome `fabric`). Nell'app/CLI va in `mcp-config.json` e **serve riavvio** (il file si carica a inizio sessione; `extensions_reload` non basta).
- **Task 6 (Fabric MCP locale):** estensione VS Code `fabric.vscode-fabric-mcp-server` → fornisce `docs_*`, `onelake_*`, `datafactory_*`, `core_*`.
- **Task 7 (Skill):** già coperto dal bundle `fabric-skills` (24 skill, 4 agent).
- **ATTENZIONE duplicati:** facile registrare 2-3 volte lo stesso server Core (nomi diversi/typo) → login multipli e tool duplicati che confondono la selezione. Tenere **un solo** server per URL (gestire da **MCP: List Servers**).
- **Drift nomi tool (doc obsoleta):** la challenge cita `docs_workloads` / `docs_workload-api-spec`; i nomi attuali sono `docs_list-item-types`, `docs_item-api-spec`, `docs_item-definitions`, `docs_platform-api-spec`, `docs_api-examples`, `docs_best-practices`.
- **Riautenticazione MCP Fabric multi-tenant:** operazione `ConnectFabric` con `clearCredential:true` + `tenantName:<tenant>.onmicrosoft.com` → login browser → scegliere l'account Contoso, **non** `@microsoft.com`.
- **Smoke test MCP:** `list_workspaces`, `list_capacities`, `docs_*`. (Verifica implicita anche delle tenant settings del Task 2, non controllabili via API con l'identità corrente.)

---

## 3. CHALLENGE 1 — Workspace as Code (modifiche al repo)

> Tutto è nel repository; qui elenco cosa è stato cambiato rispetto all'upstream e perché.

### 3.1 `runs-on` dei workflow → `ubuntu-latest`
Il fork non ha il runner self-hosted `[self-hosted, fabric-gov]` → i job restano *queued* all'infinito. Cambiati:
- `.github/workflows/validate.yml` → `runs-on: ubuntu-latest` (trigger `pull_request`)
- `.github/workflows/provision.yml` → `runs-on: ubuntu-latest` (trigger `push` su `main` + `workflow_dispatch`, `environment: production`)
- `.github/workflows/drift.yml` → `runs-on: ubuntu-latest`, trigger **solo `workflow_dispatch`** (niente schedule → esecuzione on-demand)

> Nota: per `pull_request` GitHub usa il file di workflow **del branch del PR**, quindi la modifica `runs-on` va fatta **sul branch del PR**, non solo su `main`.

### 3.2 Manifest: estensione `.yaml` obbligatoria (falso verde)
`validate.py` seleziona solo i file sotto `workspaces/` che **finiscono in `.yaml`/`.yml`**. Un file senza estensione viene ignorato → validate "verde" ma **nessun manifest processato**.

### 3.3 Manifest: campo `name` e regex
- Regex nome: `^[a-z]{2}-[a-z]{2,4}-[a-z]{2,8}-(brz|slv|gld|ndf)-(poc|dev|sit|uat|stg|prd)-[a-z0-9]{1,6}$` (6° segmento max 6 caratteri).
- Rinominare il **file** non basta: va allineato anche il campo `name:` **interno** allo YAML.
- Esempio valido usato: `it-nlyt-sample-brz-dev-gino1`.

### 3.4 Reconciliation capacity/region (blocco `region-matches-capacity`)
- La regola confronta **solo stringhe interne al repo**: manifest `region` vs `policy.approvedCapacities[<capacity>].region`. **Non** guarda la region reale su Azure. Il provisioning lega per **capacity ID**; la region è metadato cosmetico.
- La capacity reale disponibile è **una sola**: `democapacity1`, **Central US**, F16 (non "East US").
- Modifiche fatte per coerenza (Opzione "veritiera"):
  - `rules/policy.yaml` → `approvedCapacities.contoso-f2-northeurope`: `capacityId: "FILL-ME-AT-FIRST-RUN"` (così usa l'env `FABRIC_CAPACITY_ID`) e `region: centralus`.
  - `schemas/workspace.schema.json` → aggiunto `"centralus"` all'enum `region` (prima assente).
  - manifest → `region: centralus`.
- **Trappola:** il placeholder finto `capacityId: "33333333-…"` viene trattato come "valorizzato" e **impedisce** il fallback all'env var. Usare `FILL-ME-AT-FIRST-RUN` (o il GUID reale).

### 3.5 Owner reali al posto dei placeholder
Il template ha owner **finti** (`44444444-…` come Group, `workspace-owner@contoso.com` come User) → il workspace viene creato ma i **role assignment falliscono** (`PrincipalNotFound` / UPN non risolvibile) e il run risulta comunque "success" (assegnazioni best-effort in try/except).
- Sostituiti con: Group `372ef100-5498-430a-b8ce-69241f8f73ce` (Admin) + User `stdetoni@MngEnvMCAP195373.onmicrosoft.com` (Admin).
- Nota: `provision.py` è **add-only** (non rimuove mai ruoli/workspace) e `DEFAULT_OWNER_UPN` **non** viene iniettato nell'env dello step provision → gli owner arrivano **solo** dal manifest.

### 3.6 CODEOWNERS / self-approval
- `.github/CODEOWNERS` ha solo `@sdt-msft` come owner su tutti i path sensibili (`/rules/`, `/schemas/`, `/scripts/`, `/.github/`, `/workspaces/prd-*.yaml`).
- **Non si può approvare il proprio PR** → o si aggiunge un secondo code owner con write access, oppure si mergia con **privilegi admin** (bypass della ruleset `protect-main`, id `24173971`).

### 3.7 Estensione drift per i role assignment (PR #9 — merged)
`drift.py` originale rilevava solo: **unmanaged** (in tenant, non nel repo), **missing** (nel repo, non in tenant) e **drift descrizione**. Non rilevava cambi di ruolo.
- Estensione aggiunta: confronto dei **roleAssignments** per ogni workspace gestito.
- Owner attesi = owner del manifest **+** lo SP provisioner (`AZURE_CLIENT_ID`) come **Admin implicito** su ogni workspace (regola "il provisioner resta Admin"). Così il test **SP→Viewer** viene rilevato.
- Matching per chiave case-insensitive su `principal.id` **e** `userDetails.userPrincipalName` (match per UPN o Object ID senza Graph).
- Se lo SP perde Admin e non può leggere i ruoli (403), l'eccezione stessa diventa una segnalazione di drift (rc=2).
- Exit code drift = **2** (non 1) in caso di drift; il gate `if steps.drift.outputs.rc != '0'` scatta.

### 3.8 Riabilitazione workspace `hello1` (PR #11 — merged)
Il workspace `hello1`, creato dallo SP con owner placeholder, era **orfano** (invisibile all'utente perché mai assegnato). Corretto:
- `region` `northeurope` → `centralus` (sblocca `region-matches-capacity`).
- owner placeholder → gruppo admin reale + `stdetoni@…` (Admin).
- riabilitato il manifest: creato `workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml` e rimosso il placeholder senza estensione `workspaces/pt-nlyt-sample-ndf-dev-hello1`.
- Effetto collaterale positivo: sparisce il segnale drift `unmanaged: hello1`.

### 3.9 Abilitare le Issues del repo
Le **Issues erano disabilitate** → lo step di creazione issue del drift (`peter-evans/create-issue-from-file`, da `drift-report.md`, label `drift, governance`) falliva. Vanno **abilitate** in Settings.

---

## 4. Workaround tecnici trasversali (utili in erogazione)

- **`gh pr create` FALLISCE sui fork** con `GraphQL: Resource protected by organization SAML enforcement` (lookup del parent org SAML). Workaround: creare il PR via REST:
  ```
  gh api --method POST repos/<org>/<repo>/pulls -f title=… -f head=<branch> -f base=main -f body=…
  ```
- **Edit file via API** (quando non si ha il repo clonato):
  - branch: `POST git/refs -f ref=refs/heads/<name> -f sha=<mainSha>`
  - file nuovo: `PUT contents/<path> -f message -f content=<base64> -f branch=<name>` (senza `sha`)
  - file esistente/delete: aggiungere `-f sha=<fileSha>`
  - lettura raw: `-H "Accept: application/vnd.github.raw"` (evita flakiness base64/jq)
  - base64: `[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($content))`
- **Merge con privilegi admin** (bypass ruleset): `gh pr merge <n> --squash --admin --delete-branch`.
- **Header telemetria Fabric (obbligatorio con la skill):** ogni chiamata `api.fabric.microsoft.com` via `az rest` deve avere `--headers "x-ms-fabric-skill=semantic-model-authoring"`.
- **`azure/login` in `validate.yml`** ha `continue-on-error: true` / `allow-no-subscriptions: true` → il job può risultare verde anche se l'OIDC fallisce: controllare il log dello step.

---

## 5. Stato finale del repo (verificato)

- Branch: **solo `main`** (tutti i branch di lavoro/test cancellati).
- PR #9 (drift role-check) e PR #11 (riabilita hello1): **merged**.
- `rules/policy.yaml`: `capacityId: FILL-ME-AT-FIRST-RUN`, `region: centralus`.
- `schemas/workspace.schema.json`: enum region include `centralus`.
- Workflow: `validate`/`provision`/`drift` tutti su `ubuntu-latest`; `drift` solo `workflow_dispatch`.
- Variabili Actions repo-level: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `DEFAULT_OWNER_UPN`, `FABRIC_CAPACITY_ID`, `LIVE_CHECKS=true`.
- Issues: abilitate (per la creazione automatica dell'issue di drift).
