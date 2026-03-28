import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'node:http';

let wss: WebSocketServer;

/** Типы WebSocket событий */
export interface WsEvent {
  type: 'bot_status' | 'generation_progress' | 'manifest_updated' | 'reference_generated';
  data: unknown;
}

/** Инициализация WebSocket сервера */
export function setupWebSocket(server: Server): void {
  wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws) => {
    console.log('WebSocket: клиент подключился');
    ws.on('close', () => {
      console.log('WebSocket: клиент отключился');
    });
  });
}

/** Отправить событие всем подключённым клиентам */
export function broadcast(event: WsEvent): void {
  if (!wss) return;
  const message = JSON.stringify(event);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      try {
        client.send(message);
      } catch {
        // Dead connection — ignore, will be cleaned up on next close event
      }
    }
  }
}
