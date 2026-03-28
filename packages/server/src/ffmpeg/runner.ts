import { execFile } from 'node:child_process';
import { existsSync, mkdirSync, unlinkSync, writeFileSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { tmpdir } from 'node:os';
import { randomUUID } from 'node:crypto';

/** Результат выполнения FFmpeg/ffprobe */
interface ExecResult {
  stdout: string;
  stderr: string;
}

/** Элемент таймлайна */
export interface TimelineClip {
  file: string;
  startSec: number;
  endSec: number;
}

/** Результат экспорта */
export interface ExportResult {
  outputPath: string;
  duration: number;
  clipCount: number;
}

// Общие места расположения ffmpeg
const COMMON_PATHS = [
  '/usr/local/bin',
  '/opt/homebrew/bin',
  '/usr/bin',
  '/snap/bin',
];

/** Выполняет внешнюю команду и возвращает stdout/stderr */
function exec(cmd: string, args: string[]): Promise<ExecResult> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 50 * 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`${cmd} failed: ${err.message}\nstderr: ${stderr}`));
      } else {
        resolve({ stdout, stderr });
      }
    });
  });
}

/** Ищет ffmpeg/ffprobe в PATH и стандартных местах */
export function findBinary(name: 'ffmpeg' | 'ffprobe', appDir?: string): string | null {
  const ext = process.platform === 'win32' ? '.exe' : '';

  // 0. Installer mode: FFMPEG_DIR из env (задаётся лаунчером)
  if (process.env.FFMPEG_DIR) {
    const envBin = resolve(process.env.FFMPEG_DIR, `${name}${ext}`);
    if (existsSync(envBin)) return envBin;
  }

  // 0b. Installer mode: APP_ROOT_DIR/ffmpeg/
  if (process.env.APP_ROOT_DIR) {
    const installerBin = resolve(process.env.APP_ROOT_DIR, 'ffmpeg', `${name}${ext}`);
    if (existsSync(installerBin)) return installerBin;
  }

  // 1. Проверяем bin/ в директории приложения
  if (appDir) {
    const appBin = resolve(appDir, 'bin', `${name}${ext}`);
    if (existsSync(appBin)) return appBin;
  }

  // 2. Проверяем PATH
  const pathDirs = (process.env.PATH || '').split(process.platform === 'win32' ? ';' : ':');
  for (const dir of pathDirs) {
    const candidate = resolve(dir, process.platform === 'win32' ? `${name}.exe` : name);
    if (existsSync(candidate)) return candidate;
  }

  // 3. Стандартные пути (macOS/Linux)
  if (process.platform !== 'win32') {
    for (const dir of COMMON_PATHS) {
      const candidate = resolve(dir, name);
      if (existsSync(candidate)) return candidate;
    }
  }

  return null;
}

/** Находит ffmpeg, выбрасывает ошибку если не найден */
export function findFFmpeg(appDir?: string): { ffmpeg: string; ffprobe: string } {
  const ffmpeg = findBinary('ffmpeg', appDir);
  const ffprobe = findBinary('ffprobe', appDir);

  if (!ffmpeg) {
    throw new Error(
      'FFmpeg не найден. Установите: brew install ffmpeg (macOS) или apt install ffmpeg (Linux)',
    );
  }
  if (!ffprobe) {
    throw new Error(
      'FFprobe не найден. Обычно устанавливается вместе с FFmpeg.',
    );
  }

  return { ffmpeg, ffprobe };
}

/** Получает длительность видео в секундах */
export async function getVideoDuration(ffprobePath: string, filePath: string): Promise<number> {
  const { stdout } = await exec(ffprobePath, [
    '-v', 'quiet',
    '-print_format', 'json',
    '-show_format',
    filePath,
  ]);

  const info = JSON.parse(stdout);
  const duration = parseFloat(info.format?.duration || '0');
  return duration;
}

/** Обрезает один клип */
async function trimClip(
  ffmpegPath: string,
  input: string,
  output: string,
  startSec: number,
  endSec: number,
  needsTrim: boolean,
): Promise<void> {
  if (!needsTrim) {
    // Без обрезки — просто перекодируем в нужный формат для конкатенации
    await exec(ffmpegPath, [
      '-y', '-i', input,
      '-c', 'copy',
      '-avoid_negative_ts', 'make_zero',
      output,
    ]);
  } else {
    // С обрезкой — нужна перекодировка
    const duration = endSec - startSec;
    await exec(ffmpegPath, [
      '-y',
      '-ss', startSec.toFixed(3),
      '-i', input,
      '-t', duration.toFixed(3),
      '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
      '-c:a', 'aac', '-b:a', '192k',
      '-avoid_negative_ts', 'make_zero',
      output,
    ]);
  }
}

/** Обрезает и склеивает клипы в один файл */
export async function trimAndConcat(
  ffmpegPath: string,
  ffprobePath: string,
  clips: TimelineClip[],
  outputPath: string,
): Promise<void> {
  if (clips.length === 0) {
    throw new Error('Таймлайн пуст — нечего экспортировать');
  }

  const tmpDir = resolve(tmpdir(), `flow-export-${randomUUID()}`);
  mkdirSync(tmpDir, { recursive: true });

  const segmentFiles: string[] = [];

  try {
    // 1. Подготавливаем каждый клип (обрезаем если нужно)
    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i];
      if (!existsSync(clip.file)) {
        throw new Error(`Файл не найден: ${clip.file}`);
      }

      const segmentFile = resolve(tmpDir, `segment_${String(i).padStart(4, '0')}.mp4`);
      segmentFiles.push(segmentFile);

      // Определяем нужна ли обрезка
      const fullDuration = await getVideoDuration(ffprobePath, clip.file);
      const needsTrim = clip.startSec > 0.05 || (clip.endSec > 0 && Math.abs(clip.endSec - fullDuration) > 0.05);

      await trimClip(ffmpegPath, clip.file, segmentFile, clip.startSec, clip.endSec, needsTrim);
    }

    // 2. Создаём файл списка для concat
    const concatListFile = resolve(tmpDir, 'concat_list.txt');
    const concatContent = segmentFiles
      .map((f) => `file '${f.replace(/'/g, "'\\''")}'`)
      .join('\n');
    writeFileSync(concatListFile, concatContent, 'utf-8');

    // 3. Убеждаемся что выходная директория существует
    const outDir = dirname(outputPath);
    if (!existsSync(outDir)) {
      mkdirSync(outDir, { recursive: true });
    }

    // 4. Конкатенируем
    if (clips.length === 1) {
      // Один клип — просто копируем
      await exec(ffmpegPath, [
        '-y', '-i', segmentFiles[0],
        '-c', 'copy',
        outputPath,
      ]);
    } else {
      // Несколько клипов — concat demuxer
      // Перекодируем все к единому формату для надёжной склейки
      const normalizedFiles: string[] = [];
      for (let i = 0; i < segmentFiles.length; i++) {
        const normalizedFile = resolve(tmpDir, `norm_${String(i).padStart(4, '0')}.mp4`);
        await exec(ffmpegPath, [
          '-y', '-i', segmentFiles[i],
          '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
          '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1',
          '-r', '24',
          '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
          normalizedFile,
        ]);
        normalizedFiles.push(normalizedFile);
      }

      const normConcatFile = resolve(tmpDir, 'norm_concat_list.txt');
      const normConcatContent = normalizedFiles
        .map((f) => `file '${f.replace(/'/g, "'\\''")}'`)
        .join('\n');
      writeFileSync(normConcatFile, normConcatContent, 'utf-8');

      await exec(ffmpegPath, [
        '-y', '-f', 'concat', '-safe', '0',
        '-i', normConcatFile,
        '-c', 'copy',
        outputPath,
      ]);
    }
  } finally {
    // Очистка временных файлов
    try {
      const { readdirSync } = await import('node:fs');
      for (const f of readdirSync(tmpDir)) {
        try { unlinkSync(resolve(tmpDir, f)); } catch { /* ignore */ }
      }
      const { rmdirSync } = await import('node:fs');
      rmdirSync(tmpDir);
    } catch { /* ignore cleanup errors */ }
  }
}

/** Основная функция экспорта видео */
export async function exportVideo(
  projectDir: string,
  timeline: TimelineClip[],
  outputName: string,
  appDir?: string,
): Promise<ExportResult> {
  const { ffmpeg, ffprobe } = findFFmpeg(appDir);

  // Создаём директорию для экспортов
  const exportsDir = resolve(projectDir, 'exports');
  if (!existsSync(exportsDir)) {
    mkdirSync(exportsDir, { recursive: true });
  }

  // Формируем полный путь к выходному файлу
  const outputPath = resolve(exportsDir, outputName.endsWith('.mp4') ? outputName : `${outputName}.mp4`);

  // Выполняем обрезку и склейку
  await trimAndConcat(ffmpeg, ffprobe, timeline, outputPath);

  // Получаем итоговую длительность
  const duration = await getVideoDuration(ffprobe, outputPath);

  return {
    outputPath,
    duration,
    clipCount: timeline.length,
  };
}
