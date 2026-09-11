# Telegram Video Downloader

Script em Python para baixar vídeos e outras mídias pelo link de uma mensagem
do Telegram. Ele usa a sua própria conta, portanto ela precisa participar do
grupo ou canal e conseguir abrir a mensagem normalmente.

O script não acessa conversas sem permissão nem remove restrições do Telegram.
Use-o somente para conteúdo que você tem autorização para baixar.

## 1. Copiar o link correto

No Telegram Web, uma URL como esta abre apenas a conversa:

```text
https://web.telegram.org/k/#-1234567890
```

Ela não identifica uma mensagem específica e não deve ser usada no script.
Clique com o botão direito sobre a mensagem que contém o vídeo e escolha
**Copy message link** ou **Copiar link da mensagem**. O resultado será parecido
com:

```text
https://t.me/c/1234567890/123
```

Nesse exemplo fictício, `1234567890` identifica a conversa e `123` identifica a
mensagem. Links públicos, como `https://t.me/nome_do_canal/123`, também são
aceitos.

## 2. Criar as credenciais da API

1. Acesse <https://my.telegram.org/apps>.
2. Digite seu telefone no formato internacional, incluindo país e DDD.
3. Procure o código no chat oficial **Telegram**, com selo de verificação, em
   um dispositivo no qual sua conta já esteja conectada. O site avisa que esse
   código é enviado pelo Telegram, não por SMS.
4. Informe o código no site e abra **API development tools**.
5. Preencha o formulário com dados semelhantes a estes:

```text
App title: Telegram Video Downloader
Short name: tgdownloader
URL: deixe em branco
Platform: Desktop
Description: Aplicativo pessoal em Python para baixar mídias de mensagens
             do Telegram às quais minha conta possui acesso.
```

Depois de criar a aplicação, a página mostrará dois valores:

- **App api_id**: um número.
- **App api_hash**: uma sequência de letras e números.

O código de confirmação recebido no chat é temporário e não deve ser colocado
no `.env`. Ele é diferente do `api_id` e do `api_hash`.

Para consultar novamente uma aplicação já criada, entre em
<https://my.telegram.org/apps> com a mesma conta. A página **API development
tools** mostrará novamente o `api_id` e o `api_hash`.

## 3. Configurar o arquivo .env

O projeto inclui o modelo `.env.example`, que pode ser compartilhado porque
contém apenas valores fictícios. Em uma instalação nova, crie o `.env` a partir
dele:

```bash
cd /mnt/dados/telegram-video-downloader
cp .env.example .env
```

Se o seu `.env` já está preenchido, não execute o comando `cp` novamente. Abra
o arquivo para editar:

```bash
nano .env
```

Preencha os valores obtidos em **API development tools**:

```dotenv
TELEGRAM_API_ID=SEU_API_ID
TELEGRAM_API_HASH=SEU_API_HASH
```

Substitua os exemplos pelas suas credenciais. No `nano`, pressione `Ctrl+O`,
`Enter` e `Ctrl+X` para salvar e sair. O `.env` é carregado automaticamente pelo
script e está ignorado pelo Git.

## 4. Instalar

O projeto requer Python 3.10 ou mais recente. No terminal, execute:

```bash
cd /mnt/dados/telegram-video-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

A instalação só precisa ser feita uma vez. Ao abrir um terminal novo, execute
novamente `source .venv/bin/activate` antes de usar o script.

## 5. Baixar um vídeo

Com o ambiente virtual ativado, passe o link copiado da mensagem:

```bash
python telegram_downloader.py "https://t.me/c/1234567890/123"
```

Na primeira execução, o Telethon solicitará:

1. Seu telefone no formato internacional, seguindo o modelo
   `+[CODIGO_DO_PAIS][DDD][NUMERO]` e substituindo todos os campos pelos
   números corretos.
2. Um novo código de login enviado ao chat oficial **Telegram** dentro do
   aplicativo. Esse código não é enviado por SMS e não é o `api_hash`.
3. Sua senha de verificação em duas etapas, caso esteja ativada.

Quando aparecer `Please enter your phone (or bot token):`, informe o telefone.
A menção a bot token faz parte da mensagem genérica do Telethon; este projeto
autentica a sua conta de usuário e não precisa de token de bot.

O login fica salvo em `.telegram_downloader.session`, então normalmente essas
perguntas não aparecem nos próximos downloads. O arquivo baixado é colocado na
pasta `downloads`.

Para escolher outra pasta de destino:

```bash
python telegram_downloader.py "LINK_DA_MENSAGEM" --output /caminho/para/videos
```

## Problemas comuns

- **Conversa privada não encontrada:** confirme que a mesma conta usada no
  script participa do grupo ou canal e consegue abrir o link.
- **Mensagem não encontrada:** copie novamente o link da mensagem, não a URL da
  barra de endereços do Telegram Web.
- **Mensagem sem mídia:** confirme que o link aponta diretamente para a mensagem
  que contém o vídeo ou arquivo.
- **Credenciais ausentes:** verifique se o `.env` está na mesma pasta de
  `telegram_downloader.py` e se os dois campos foram preenchidos.
- **Dependência ausente:** ative a `.venv` e execute novamente
  `pip install -r requirements.txt`.

## Segurança

Não compartilhe o `api_hash`, códigos de login, senha de verificação em duas
etapas, arquivo `.env` ou arquivo `.telegram_downloader.session`. Quem obtiver
o arquivo de sessão pode conseguir acessar sua conta. Para encerrar sessões que
você não reconhece, use **Configurações > Dispositivos** no Telegram.

O `.gitignore` impede que sejam enviados ao Git o `.env`, a `.venv`, os arquivos
de sessão (`*.session` e `*.session-journal`) e a pasta `downloads`. O arquivo
`.env.example` permanece versionável por conter somente exemplos.
