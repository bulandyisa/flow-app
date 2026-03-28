import mammoth from 'mammoth';
import { readFileSync } from 'node:fs';

export interface ParsedScreenplay {
  text: string;       // Чистый текст
  html: string;       // HTML с форматированием
  paragraphs: string[];  // Разбито по абзацам
}

/** Парсит .docx файл и возвращает текст + HTML */
export async function parseDocx(filePath: string): Promise<ParsedScreenplay> {
  const buffer = readFileSync(filePath);

  const [textResult, htmlResult] = await Promise.all([
    mammoth.extractRawText({ buffer }),
    mammoth.convertToHtml({ buffer }),
  ]);

  const paragraphs = textResult.value
    .split('\n')
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  return {
    text: textResult.value,
    html: htmlResult.value,
    paragraphs,
  };
}
