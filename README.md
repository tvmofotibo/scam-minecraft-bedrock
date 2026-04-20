# 🛡️ MC-SCAN BR v5.3 (White-Hat)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![NodeJS](https://img.shields.io/badge/node.js-6DA55F?style=for-the-badge&logo=node.js&logoColor=white)

**MC-SCAN** é um ecossistema distribuído de alta performance projetado para identificar e notificar servidores Minecraft Bedrock vulneráveis ou expostos no Brasil. O objetivo é puramente educacional e focado em segurança (White-Hat), alertando proprietários sobre a importância de ativar a Whitelist.

---

## 🚀 Funcionalidades

- **Arquitetura Master/Worker**: Escala horizontalmente. Adicione quantos dispositivos (celulares, RPi, VPS) quiser para acelerar o scan.
- **Scan Massivo**: Baixa automaticamente a lista atualizada de todos os blocos de IP (CIDRs) brasileiros.
- **Painel Central (Cyberpunk UI)**: Monitoramento em tempo real via dashboard web moderno.
- **Fila Gerenciada via Redis**: Distribuição inteligente de tarefas, garantindo que nenhum IP seja ignorado ou repetido.
- **Notificação Automática**: Bot integrado que entra nos servidores e envia mensagens de alerta de segurança.

---

## 🛠️ Arquitetura do Sistema

1.  **Master (Central)**: Hospeda o Redis, a API de recebimento e o Dashboard Web.
2.  **Producer**: Quebra os blocos de IP do Brasil em sub-redes `/24` e alimenta o Redis.
3.  **Workers (Escravos)**: Consomem a fila do Redis, realizam o handshake RakNet e reportam sucessos para a Central.
4.  **Bot Notifier**: Percorre a lista de encontrados e realiza a entrada "White-Hat" para aviso.

---

## 📦 Instalação e Uso

O projeto conta com um orquestrador automático (`start.py`) que gerencia dependências (incluindo correções para Debian ARM).

### 1. Clonar o repositório
```bash
git clone https://github.com/seu-usuario/minecraft-scanner-br.git
cd minecraft-scanner-br
```

### 2. Iniciar o Painel Central (Servidor Master)
No servidor principal (que deve ter o Redis instalado):
```bash
python3 start.py
```
- Selecione a **Opção 1**.
- O sistema irá instalar as dependências, baixar os IPs, popular o Redis e abrir o painel em `http://seu-ip:5000`.

### 3. Adicionar Workers (Dispositivos Escravos)
Em qualquer outro dispositivo com Python:
```bash
python3 start.py
```
- Selecione a **Opção 2**.
- Informe o IP do Servidor Master e a chave de API (Padrão: `MC-SCAN-2026`).

---

## 🖥️ Painel de Controle (Dashboard)

A interface web oferece:
- **Total de Servidores**: Contagem global de detecções únicas.
- **Fila de Tarefas**: Quantidade de blocos de IP pendentes no Redis.
- **Live Feed**: Tabela em tempo real com IP, Porta, MOTD e contagem de jogadores dos últimos encontrados.

---

## 🛡️ Aviso Legal (Disclaimer)

Este software foi desenvolvido para fins de **pesquisa e notificação ética de segurança**. O autor não se responsabiliza pelo uso indevido da ferramenta. A entrada automática nos servidores é configurada para enviar apenas mensagens informativas de segurança (White-Hat).

---

## 🤝 Contribuindo

Sinta-se à vontade para abrir Issues ou enviar Pull Requests para:
- Otimização do protocolo RakNet.
- Melhorias na interface web.
- Novos métodos de notificação.

---
**Desenvolvido para a comunidade brasileira de Minecraft.** 🇧🇷
