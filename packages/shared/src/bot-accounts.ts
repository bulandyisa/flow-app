/**
 * Сопоставление бот-id → Google-аккаунт.
 * 6 ботов работают на 2 Google-аккаунтах:
 *   - Боты 1, 2, 5 → Google-аккаунт 1
 *   - Боты 3, 4, 6 → Google-аккаунт 2
 */
export type GoogleAccount = 1 | 2;

export const BOT_TO_GA: Record<number, GoogleAccount> = {
  1: 1,
  2: 1,
  3: 2,
  4: 2,
  5: 1,
  6: 2,
};

/** Возвращает номер Google-аккаунта для данного бота. Fallback: 1. */
export function gaForBot(botAccount: number): GoogleAccount {
  return BOT_TO_GA[botAccount] ?? 1;
}
