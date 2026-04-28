import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE_URL } from '@/api/client';

export type WsMessage = {
  id?: string;
  type: 'user_message' | 'ai_message' | 'system' | 'ready' | 'pong' | 'error';
  sender_role?: string;
  sender_display_name?: string;
  message_text?: string;
  payload?: {
    text: string;
    citations: unknown[];
    trigger: string;
    metadata: Record<string, unknown>;
  };
  event?: string;
};

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error';

type Participant = {
  user_id: string;
  role: string;
};

const WS_BASE_URL = API_BASE_URL.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
const MAX_RETRIES = 5;

export function useWebSocketChat(
  caseId: string,
  token: string | null,
  options: {
    senderRole?: string;
    inviteSent?: boolean;
    participants?: Participant[];
  } = {}
) {
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [status, setStatus] = useState<WsStatus>('closed');
  const wsRef = useRef<WebSocket | null>(null);
  const senderRole = options.senderRole ?? 'owner';
  const inviteSent = options.inviteSent ?? false;
  const participants = useMemo(
    () => options.participants ?? [{ user_id: 'owner-1', role: senderRole }],
    [options.participants, senderRole]
  );

  useEffect(() => {
    if (!token || !caseId) {
      setStatus('closed');
      return;
    }

    const authToken = token;
    let retries = 0;
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    function openConnection() {
      if (cancelled) return;
      setStatus('connecting');
      const ws = new WebSocket(`${WS_BASE_URL}/ws/cases/${caseId}?token=${encodeURIComponent(authToken)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        retries = 0;
        setStatus('open');
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const parsed = JSON.parse(String(event.data)) as WsMessage;
          if (parsed.type === 'ready' || parsed.type === 'pong') return;
          setMessages((prev) => [
            ...prev,
            { ...parsed, id: parsed.id || `${Date.now()}-${Math.random()}` },
          ]);
        } catch {
          // Ignore malformed frames from transient network states.
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus('closed');
        if (retries < MAX_RETRIES) {
          const delay = Math.min(1500 * 2 ** retries, 15000);
          retries += 1;
          retryTimer = setTimeout(openConnection, delay);
        } else {
          setStatus('error');
        }
      };
    }

    openConnection();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, [caseId, token]);

  const sendMessage = useCallback((text: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({
      type: 'chat',
      message_text: text,
      sender_role: senderRole,
      invite_sent: inviteSent,
      participants,
      run_ai: true,
    }));
    return true;
  }, [inviteSent, participants, senderRole]);

  return { messages, sendMessage, status };
}
