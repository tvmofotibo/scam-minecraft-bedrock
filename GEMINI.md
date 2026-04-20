# Projeto Minecraft Scanner (White-Hat) - Status v5.3

Este documento registra o estado atual do projeto de varredura massiva e notificação distribuída de servidores Minecraft Bedrock no Brasil.

## 📊 Status Atual (20/04/2026)
- **Versão:** v5.3 (Arquitetura Distribuída & Alta Performance).
- **Servidores Encontrados:** 22 (registrados em `project/servers.json`).
- **Escopo:** Varredura completa de todos os CIDRs brasileiros (baixados dinamicamente).
- **Dashboard:** Modernizado (Cyberpunk UI) na porta 5000.

## 🚀 Como Operar (O Novo Orquestrador)

Agora o projeto utiliza um ponto de entrada unificado que gerencia dependências e modos de operação.

### 1. Iniciar o Orquestrador
```bash
python3 start.py
```

### 2. Modos de Operação:
- **Opção 1 (MASTER):** Inicia o Redis, o Dashboard Web, atualiza a lista de IPs do Brasil, popula a fila de tarefas e inicia um worker local.
- **Opção 2 (WORKER):** Transforma o dispositivo em um escravo de escaneamento. Pede o IP do Master e começa a processar a fila.

## 🛠️ Arquitetura Técnica (v5.3)
- **Fila de Tarefas:** Redis (Lista `mc_scan_tasks`).
- **Comunicação:** API Flask com autenticação `X-API-Key` (MC-SCAN-2026).
- **Workers:** Assíncronos (`asyncio` + `aiohttp`), otimizados para Debian ARM e dispositivos de baixo consumo.
- **Deduplicação:** Verificação via `set()` em memória no Master para performance máxima.
- **Lazy Saving:** O Master sincroniza os dados com o disco a cada 10 segundos para evitar gargalos de I/O.

## 📂 Estrutura de Arquivos
- `start.py`: Orquestrador central e instalador de dependências.
- `project/web/app.py`: Servidor Master (API e Painel Web).
- `project/scanner/worker.py`: Script de escaneamento (Escravo).
- `project/scanner/producer.py`: Distribuidor de blocos de IP.
- `project/scanner/update_ips.py`: Atualizador da base de IPs brasileiros.
- `project/bot/bot.js`: Bot White-Hat (Protocolo Bedrock).

## 📝 Próximos Passos
1. Adicionar múltiplos workers em diferentes conexões de internet para acelerar a varredura total do país.
2. Rodar o `project/bot/bot.js` periodicamente para notificar os novos alvos detectados.
3. Monitorar a fila através do Dashboard em `http://seu-ip:5000`.
---
*Nota: Este projeto é para fins educacionais e de segurança (White-Hat). Sempre respeite os termos de serviço das redes escaneadas.*
