interface SceneHeaderProps {
  sceneId: string;
  label?: string;
  color?: string;
  clipCount: number;
}

/** Палитра цветов для сцен (15 цветов) */
const SCENE_PALETTE = [
  '#6366F1', '#EC4899', '#F59E0B', '#10B981', '#3B82F6',
  '#8B5CF6', '#EF4444', '#14B8A6', '#F97316', '#06B6D4',
  '#84CC16', '#E879F9', '#FB923C', '#22D3EE', '#A78BFA',
];

function getSceneColor(sceneId: string, customColor?: string): string {
  if (customColor) return customColor;
  const num = parseInt(sceneId.replace(/\D/g, ''), 10) || 0;
  return SCENE_PALETTE[num % SCENE_PALETTE.length];
}

export function SceneHeader({ sceneId, label, color, clipCount }: SceneHeaderProps) {
  const sceneColor = getSceneColor(sceneId, color);

  return (
    <div
      className="mt-6 mb-3 pl-3 py-1"
      style={{ borderLeft: `4px solid ${sceneColor}` }}
    >
      <h3 className="text-lg font-semibold text-gray-200">
        {label || sceneId}
        <span className="ml-2 text-sm font-normal text-gray-500">
          {clipCount} {clipCount === 1 ? 'клип' : 'клипов'}
        </span>
      </h3>
    </div>
  );
}
