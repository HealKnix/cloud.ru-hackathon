import {
  type ChatHistoryItem,
  type QuickPrompt,
  type SendMessagePayload,
} from '@/entities/chat/types';

const quickPrompts: QuickPrompt[] = [
  {
    id: 'pitch',
    title: 'Craft persuasive email',
    prompt:
      'Write a persuasive email to convince potential customers to try our service.',
    tone: 'Confident',
  },
  {
    id: 'training',
    title: 'Training video outline',
    prompt:
      'Draft a script for a 2-minute training video on how to use our analytics workspace.',
    tone: 'Instructional',
  },
  {
    id: 'demo',
    title: '30s promo script',
    prompt:
      'Create a 30-second commercial script promoting the new product update.',
    tone: 'Promo',
  },
  {
    id: 'explain',
    title: 'Explain AI simply',
    prompt:
      'Explain what our AI agent does in one paragraph with 3 bullet points.',
    tone: 'Simple',
  },
];

const historyItems: ChatHistoryItem[] = [
  // История будет появляться, когда бэкенд вернёт реальные диалоги.
];

export async function fetchMockQuickPrompts(): Promise<QuickPrompt[]> {
  await delay(120);
  return quickPrompts;
}

export async function fetchMockHistory(): Promise<ChatHistoryItem[]> {
  await delay(120);
  return historyItems;
}

const pick = <T>(arr: T[]) => arr[Math.floor(Math.random() * arr.length)];

export async function* mockChatStream(
  payload: SendMessagePayload,
): AsyncGenerator<string> {
  const base = [
    'Принял запрос и подключил инструменты: ',
    payload.serverIds.length ? payload.serverIds.join(', ') : 'без MCP',
    '. ',
    'Вот как предлагаю двинуться: ',
  ].join('');

  const steps = [
    'Проверяю контекст в CRM, чтобы понять, кто заказчик.',
    'Запрашиваю свежий прогноз cash-flow через finance.forecast.',
    'Готовлю набор KPI для контроля результата.',
    'Собираю черновик письма для клиента и внутренний чек-лист.',
  ];

  const text = `${base}${pick(
    steps,
  )}. Если нужно — могу дернуть еще /funnel.inspect или /invoice.create.`;
  const parts = text.split(' ');

  for (const part of parts) {
    await new Promise((res) => setTimeout(res, 120));
    yield `${part} `;
  }
}

async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
