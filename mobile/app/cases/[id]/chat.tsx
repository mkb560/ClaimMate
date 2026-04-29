import * as Clipboard from 'expo-clipboard';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ScrollView, Share, StyleSheet, Text, TextInput, View } from 'react-native';
import {
  CaseMemberEntry,
  ChatMessageRow,
  createInvite,
  getCaseMembers,
  getChatMessages,
} from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { CaseStepper } from '@/components/CaseStepper';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Loading } from '@/components/Loading';
import { Screen } from '@/components/Screen';
import { useWebSocketChat, WsMessage } from '@/hooks/useWebSocketChat';
import { colors, radius, spacing } from '@/theme/theme';

type DisplayMessage = {
  id: string;
  role: 'user' | 'ai' | 'system';
  text: string;
  senderName?: string;
};

function rowToDisplay(row: ChatMessageRow): DisplayMessage {
  return {
    id: row.id,
    role: row.message_type === 'ai' ? 'ai' : 'user',
    text: row.message_type === 'ai' ? row.ai_payload?.text || row.body_text : row.body_text,
    senderName: row.message_type === 'ai' ? 'ClaimMate' : row.sender_display_name || row.sender_role || 'User',
  };
}

function wsToDisplay(message: WsMessage): DisplayMessage | null {
  const id = message.id || `${Date.now()}-${Math.random()}`;
  if (message.type === 'user_message') {
    return {
      id,
      role: 'user',
      text: message.message_text || '',
      senderName: message.sender_display_name || message.sender_role || 'User',
    };
  }
  if (message.type === 'ai_message' && message.payload) {
    return {
      id,
      role: 'ai',
      text: message.payload.text,
      senderName: 'ClaimMate',
    };
  }
  if (message.type === 'system' && message.event) {
    return { id, role: 'system', text: message.event };
  }
  return null;
}

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const caseId = String(id);
  const { token, user } = useAuth();
  const [history, setHistory] = useState<DisplayMessage[]>([]);
  const [members, setMembers] = useState<CaseMemberEntry[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteLink, setInviteLink] = useState('');
  const [error, setError] = useState('');

  const currentMember = members.find((member) => member.user_id === user?.user_id);
  const senderRole = currentMember?.role ?? 'owner';
  const participants = useMemo(
    () => members.length > 0
      ? members.map((member) => ({ user_id: member.user_id, role: member.role }))
      : [{ user_id: user?.user_id ?? 'owner-1', role: senderRole }],
    [members, senderRole, user?.user_id]
  );
  const { messages: wsMessages, sendMessage, status } = useWebSocketChat(caseId, token, {
    senderRole,
    inviteSent: participants.length > 1 || Boolean(inviteLink),
    participants,
  });

  useEffect(() => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const [chat, loadedMembers] = await Promise.all([
          getChatMessages(caseId),
          getCaseMembers(caseId).catch(() => [] as CaseMemberEntry[]),
        ]);
        if (active) {
          setHistory(chat.messages.map(rowToDisplay));
          setMembers(loadedMembers);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load chat');
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [caseId, token]);

  const allMessages = useMemo(() => {
    const historyIds = new Set(history.map((message) => message.id));
    const live = wsMessages.flatMap((message) => {
      const display = wsToDisplay(message);
      return display && !historyIds.has(display.id) ? [display] : [];
    });
    return [...history, ...live];
  }, [history, wsMessages]);

  function handleSend() {
    const text = input.trim();
    if (!text) return;
    const sent = sendMessage(text);
    if (sent) setInput('');
  }

  async function handleInvite() {
    setInviteBusy(true);
    setError('');
    try {
      const invite = await createInvite(caseId, 'adjuster');
      const link = `claimmate://invites?token=${encodeURIComponent(invite.token)}`;
      setInviteLink(link);
      await Clipboard.setStringAsync(invite.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create invite failed');
    } finally {
      setInviteBusy(false);
    }
  }

  async function shareInvite() {
    if (!inviteLink) return;
    await Share.share({
      message: `Join my ClaimMate case: ${inviteLink}`,
    });
  }

  if (loading) return <Loading />;

  return (
    <Screen scroll={false}>
      <View style={styles.container}>
        <AppHeader />
        <CaseStepper caseId={caseId} current={3} />
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Step 4: AI Chat</Text>
            <Text style={styles.status}>Connection: {status}</Text>
          </View>
          <Button title="Invite" variant="secondary" loading={inviteBusy} onPress={handleInvite} />
        </View>
        <ErrorBanner message={error} />
        {inviteLink ? (
          <Card style={styles.inviteCard}>
            <Text style={styles.inviteTitle}>Invite token copied</Text>
            <Text style={styles.inviteText}>{inviteLink}</Text>
            <Button title="Share Invite" variant="secondary" onPress={shareInvite} />
          </Card>
        ) : null}
        <ScrollView
          style={styles.messages}
          contentContainerStyle={styles.messagesContent}
          keyboardShouldPersistTaps="handled"
        >
          {allMessages.length === 0 ? (
            <Text style={styles.empty}>No messages yet. Try: @AI what should I do next?</Text>
          ) : (
            allMessages.map((message) => (
              <View
                key={message.id}
                style={[
                  styles.bubble,
                  message.role === 'user' && styles.userBubble,
                  message.role === 'ai' && styles.aiBubble,
                  message.role === 'system' && styles.systemBubble,
                ]}
              >
                <Text style={[styles.sender, message.role === 'user' && styles.userSender]}>
                  {message.senderName || message.role}
                </Text>
                <Text style={[styles.messageText, message.role === 'user' && styles.userMessageText]}>
                  {message.text}
                </Text>
              </View>
            ))
          )}
        </ScrollView>
        <View style={styles.inputRow}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask about your claim..."
            placeholderTextColor="#94a3b8"
            style={styles.input}
            multiline
          />
          <Button title="Send" onPress={handleSend} disabled={status !== 'open' || !input.trim()} />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '900',
  },
  status: {
    color: colors.muted,
    fontSize: 12,
  },
  inviteCard: {
    gap: spacing.sm,
  },
  inviteTitle: {
    color: colors.text,
    fontWeight: '900',
  },
  inviteText: {
    color: colors.muted,
    fontSize: 12,
  },
  messages: {
    flex: 1,
  },
  messagesContent: {
    gap: spacing.sm,
    paddingVertical: spacing.sm,
  },
  empty: {
    color: colors.muted,
    textAlign: 'center',
    marginTop: 40,
  },
  bubble: {
    borderRadius: radius.md,
    gap: 4,
    maxWidth: '88%',
    padding: spacing.md,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: colors.blue,
  },
  aiBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#eef2ff',
  },
  systemBubble: {
    alignSelf: 'center',
    backgroundColor: colors.surfaceSoft,
  },
  sender: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  messageText: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 21,
  },
  userSender: {
    color: '#bfdbfe',
  },
  userMessageText: {
    color: '#fff',
  },
  inputRow: {
    alignItems: 'flex-end',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  input: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    flex: 1,
    maxHeight: 120,
    minHeight: 50,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
});
