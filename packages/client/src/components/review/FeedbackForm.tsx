interface FeedbackFormProps {
  clipId: string;
  component: string;
  value: string;
  onChange: (value: string) => void;
}

export function FeedbackForm({ clipId, component, value, onChange }: FeedbackFormProps) {
  return (
    <div className="mt-2">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Оставь пустым чтобы принять выбранный вариант"
        className="w-full px-3 py-2 bg-surface rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm resize-none placeholder:text-gray-600"
        rows={2}
      />
    </div>
  );
}
