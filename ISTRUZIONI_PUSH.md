# Pubblicare il progetto su GitHub

Questa cartella e' il tuo repository originale (5 commit di storia intatti,
branch `main`) con sopra applicato il refactoring dello schema.
**Non sostituirla** con lo zip precedente: quello non conteneva `.git`.

## Prima di iniziare — controlli gia' fatti

- `.env` e' in `.gitignore` e **non e' mai stato committato**: verificato su
  tutta la history. Nessuna credenziale Neon o `DJANGO_SECRET_KEY` da ripulire.
- `.env.example` contiene solo placeholder (`change-me`).
- Aggiunto `.claude/` a `.gitignore`: sono preferenze locali dell'editor.
- Nessuna stringa `postgresql://`, `neon.tech` o `npg_` nei file da committare.

## 1. Crea il repository su GitHub

Fallo tu dall'interfaccia: **New repository** -> nome `English-Web-App` ->
**Private** (consigliato: il progetto e' collegato a un database reale) ->
**non** spuntare "Add a README", "Add .gitignore" o "Choose a license",
altrimenti il primo push va in conflitto con la storia esistente.

Non creare il repo da riga di comando con un token: la creazione di account e
l'inserimento di credenziali vanno fatti da te nell'interfaccia di GitHub.

## 2. Verifica cosa stai per committare

```bash
cd English-Web-App
git status
git diff --stat
```

Attenzione: il changeset contiene **due lavori diversi**:

1. modifiche tue non ancora committate (migration `0005`, configurazione Neon
   in `settings.py`, ristrutturazione del frontend in `components/`, `pages/`,
   `hooks/`, `context/`, `utils/`);
2. il refactoring dello schema descritto in `COMMIT_MESSAGE.txt`.

Se vuoi tenerli separati, committa prima il punto 1 e poi il punto 2 usando
`git add -p` per selezionare le porzioni. Se preferisci fare presto, un commit
unico va bene: la storia resta comunque leggibile grazie al messaggio.

## 3. Commit

```bash
git add -A
git commit -F COMMIT_MESSAGE.txt
```

## 4. Collega il remote e pubblica

Sostituisci `TUO-UTENTE` con il tuo nome utente GitHub.

```bash
git remote add origin https://github.com/TUO-UTENTE/English-Web-App.git
git branch -M main
git push -u origin main
```

Se GitHub chiede le credenziali, usa un **Personal Access Token** (Settings ->
Developer settings -> Personal access tokens -> Fine-grained, scope
`Contents: Read and write`) al posto della password: le password non sono piu'
accettate per il push via HTTPS. In alternativa configura una chiave SSH e usa
`git@github.com:TUO-UTENTE/English-Web-App.git`.

## 5. Dopo il push

- **Secret scanning**: Settings -> Code security -> abilita "Secret scanning" e
  "Push protection". Blocca automaticamente il push di chiavi in futuro.
- **CI**: il repo contiene gia' `.github/workflows/ci.yml`. Girera' al primo
  push. Se il workflow ha bisogno del database, aggiungi le variabili in
  Settings -> Secrets and variables -> Actions. Non metterle mai nel file YAML.
- **I 2 test rossi**: `test_password_policy` fallisce su due casi. Sono
  **preesistenti** a questo refactoring (il serializer richiede `nome` e
  `cognome` obbligatori, il test non li invia). Se la CI deve essere verde al
  primo colpo, sistemali prima del push oppure aprili come issue.

## Rollback

- Codice: `git reset --hard d439c83` riporta all'ultimo commit noto.
- Database: su Neon esiste il branch `pre-refactor-0006-backup`
  (`br-flat-math-b15zwyw3`) con lo schema precedente alla migration 0006.
