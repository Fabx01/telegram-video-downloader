# Telegram Video Downloader

<p align="center">
  <a href="https://www.python.org"><img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat&logo=python&logoColor=white" /></a>
  <a href="https://docs.telethon.dev"><img alt="Telethon 1.42+" src="https://img.shields.io/badge/Telethon-1.42%2B-2AABEE.svg?style=flat&logo=telegram&logoColor=white" /></a>
  <img alt="Interface CLI" src="https://img.shields.io/badge/Interface-CLI-4B5563.svg?style=flat" />
  <img alt="Download em fila" src="https://img.shields.io/badge/Downloads-Fila-22C55E.svg?style=flat" />
</p>

Script em Python para baixar vídeos e outras mídias pelo link de uma mensagem
do Telegram. Ele usa a sua própria conta, portanto ela precisa participar do
grupo ou canal e conseguir abrir a mensagem normalmente.

Tipos de mídia aceitos:

- Vídeos
- Fotos
- Áudios e mensagens de voz
- PDFs e outros documentos
- GIFs e alguns tipos de arquivos anexados

O script não acessa conversas sem permissão nem remove restrições do Telegram.

## 1. Copiar o link correto

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

Para consultar novamente uma aplicação já criada, entre em
<https://my.telegram.org/apps> com a mesma conta. A página **API development
tools** mostrará novamente o `api_id` e o `api_hash`.

## 3. Configurar o arquivo .env

Crie um arquivo chamado `.env` na mesma pasta de `telegram_downloader.py`, abra e preencha os valores obtidos em **API
development tools**:

```dotenv
TELEGRAM_API_ID=SEU_API_ID
TELEGRAM_API_HASH=SEU_API_HASH
```

Substitua os exemplos pelas suas credenciais e salve o arquivo.

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

## 5. Primeira autenticação

Na primeira vez que qualquer forma de download for usada, o Telethon
solicitará:

1. Seu telefone no formato internacional, seguindo o modelo
   `+[CODIGO_DO_PAIS][DDD][NUMERO]` e substituindo todos os campos pelos
   números corretos.
2. Um novo código de login enviado ao **chat oficial Telegram** dentro do aplicativo.
3. Sua senha de verificação em duas etapas, caso esteja ativada.

Quando aparecer `Please enter your phone (or bot token):`, informe o telefone. deposi pedira o token recebido no chat oficial do telegram

O login fica salvo em `.telegram_downloader.session`, então normalmente essas
perguntas não aparecem nos próximos downloads.

## 6. Forma 1: baixar pelo link direto

Com o ambiente virtual ativado, passe o link copiado da mensagem:

```bash
python telegram_downloader.py "https://t.me/c/1234567890/123"
```

Essa forma é indicada para baixar uma mensagem específica. Também é possível
passar vários links diretamente no mesmo comando:

```bash
python telegram_downloader.py "LINK_VIDEO_1" "LINK_VIDEO_2" "LINK_VIDEO_3"
```

Para escolher outra pasta de destino:

```bash
python telegram_downloader.py "LINK_VIDEO" --output /caminho/para/videos
```

## 7. Forma 2: baixar uma lista automaticamente

Use o arquivo `links/links.txt` para montar uma fila. Coloque um link do telegram por linha:

```text
# Linhas vazias e linhas iniciadas com # são ignoradas.
https://t.me/c/1234567890/101
https://t.me/c/1234567890/102
https://t.me/c/1234567890/103
```

Se nenhum arquivo de lista existir, a primeira execução sem argumentos cria
automaticamente `links/links.txt` e pede que ele seja preenchido. Também é
possível criar a pasta manualmente:

```bash
mkdir -p links
```

Em seguida, crie `links/links.txt` com o editor de sua preferência.

Para iniciar o download dos links do arquivo links.txt, execute o script sem passar um link:

```bash
python telegram_downloader.py
```

O script procura todos os arquivos `*.txt` dentro de `links/`, ignora linhas
vazias, comentários e links repetidos, informa quantos links válidos encontrou
e baixa um vídeo por vez. Se um link falhar, os próximos continuam, e um resumo
é exibido ao final.

### Controlar a fila com !pause

Para deixar todas as aulas preparadas e baixar somente uma parte da lista,
coloque `!pause` em uma linha. Os links acima da marcação entram na fila e os
links abaixo ficam pausados:

```text
https://t.me/c/1234567890/101
https://t.me/c/1234567890/102
https://t.me/c/1234567890/103
!pause # continuar a partir daqui futuramente
https://t.me/c/1234567890/104
https://t.me/c/1234567890/105
```

Nesse exemplo, as três primeiras aulas são processadas e as duas últimas ficam
pausadas. Para liberar mais aulas, mova `!pause` para baixo e execute novamente.
Os arquivos completos serão ignorados e o download continuará pelos próximos.

Cada arquivo possui sua própria marcação. Assim, `links/redes.txt` pode estar
pausado depois da primeira aula enquanto `links/logica.txt` está pausado depois
da quarta. Ao processar os dois arquivos, cada fila respeita o seu próprio
limite. A marcação também aceita letras maiúsculas e um comentário, como
`!PAUSE # assistir antes de continuar`.

Se `!pause` estiver na primeira linha, nenhum download daquele arquivo será
iniciado. Se a marcação não existir, todos os links do arquivo serão
processados.

Também é possível informar uma lista específica:

```bash
python telegram_downloader.py --links-file links/minhas_aulas.txt
```

O parâmetro `--links-file` pode ser repetido para combinar mais de uma lista:

```bash
python telegram_downloader.py \
  --links-file links/modulo_1.txt \
  --links-file links/modulo_2.txt
```

Sem `--links-file`, o comando `python telegram_downloader.py` procura todos os
arquivos `.txt` da pasta `links/` e respeita o `!pause` de cada um.

Mantenha as listas dentro de `links/`, pois essa pasta está no `.gitignore` e
não será publicada acidentalmente.

## 8. Downloads

Os arquivos ficam em `downloads/`. Para salvar em outro local, use
`--output /caminho/para/videos`.

Para cancelar, pressione **Ctrl+C**. Execute o mesmo comando para continuar
a fila: arquivos completos são ignorados e os incompletos recomeçam do zero.

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
- **Nenhum link informado:** crie `links/links.txt`, coloque um link por linha e
  execute o script sem argumentos.

## Segurança

Não compartilhe o `api_hash`, códigos de login, senha de verificação em duas
etapas, arquivo `.env` ou arquivo `.telegram_downloader.session`. Quem obtiver
o arquivo de sessão pode conseguir acessar sua conta. Para encerrar sessões que
você não reconhece, use **Configurações > Dispositivos** no Telegram.
