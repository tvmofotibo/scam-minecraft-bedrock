const bedrock = require('bedrock-protocol');
const fs = require('fs');
const path = require('path');

const SERVERS_FILE = path.join(__dirname, '../servers.json');

async function notifyServer(server, index, allServers) {
    if (server.notified === true) return; // Pula se já foi notificado

    return new Promise((resolve) => {
        const targetPort = server.port || 19132;
        console.log(`[*] Notificando ${server.ip}:${targetPort}...`);
        
        const client = bedrock.createClient({
            host: server.ip,
            port: targetPort,
            username: 'AlertaSeguro',
            offline: true,
            connectTimeout: 7000
        });

        const timeout = setTimeout(() => {
            client.disconnect();
            resolve();
        }, 10000);

        client.on('spawn', () => {
            setTimeout(() => {
                client.queue('text', {
                    type: 'chat', needs_translation: false, source_name: '', xuid: '', platform_chat_id: '',
                    message: '§c[AVISO]§f Servidor detectado em varredura de seguranca.'
                });
                
                setTimeout(() => {
                    client.queue('text', {
                        type: 'chat', needs_translation: false, source_name: '', xuid: '', platform_chat_id: '',
                        message: '§eAtive a Whitelist para evitar acessos indesejados.'
                    });
                    
                    console.log(`[✔] Mensagem enviada para ${server.ip}`);
                    server.notified = true; // Marca como notificado
                    
                    // Salva o progresso imediatamente
                    fs.writeFileSync(SERVERS_FILE, JSON.stringify(allServers, null, 4));
                    
                    clearTimeout(timeout);
                    client.disconnect();
                    resolve();
                }, 1000);
            }, 2000);
        });

        client.on('error', () => {
            clearTimeout(timeout);
            resolve();
        });
    });
}

async function run() {
    console.log("=== BOT DE NOTIFICAÇÃO WHITE-HAT ===");
    if (!fs.existsSync(SERVERS_FILE)) return;

    const data = fs.readFileSync(SERVERS_FILE, 'utf8');
    let servers = JSON.parse(data);
    
    // Filtra apenas os que ainda não foram notificados
    const pending = servers.filter(s => !s.notified);
    console.log(`[*] Servidores pendentes: ${pending.length}`);

    for (let i = 0; i < servers.length; i++) {
        await notifyServer(servers[i], i, servers);
    }
    console.log("[✔] Ciclo de notificações finalizado.");
}

run();
