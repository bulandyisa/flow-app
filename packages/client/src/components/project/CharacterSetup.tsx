import { useState } from 'react';
import { Plus, Trash2, Upload, User } from 'lucide-react';
import { api } from '@/api/client';

interface Character {
  id: string;
  name: string;
  nameRu: string;
  clothing: string;
  description: string;
  baseImage: string | null;
  status: string;
}

interface CharacterSetupProps {
  projectId: string;
  characters: Character[];
  onUpdate: () => void;
}

export function CharacterSetup({ projectId, characters, onUpdate }: CharacterSetupProps) {
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: '', nameRu: '', clothing: '', description: '' });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const handleAdd = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await api.addCharacter(projectId, form, imageFile || undefined);
      setForm({ name: '', nameRu: '', clothing: '', description: '' });
      setImageFile(null);
      setShowAdd(false);
      onUpdate();
    } catch (err) {
      alert(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (charId: string) => {
    await api.deleteCharacter(projectId, charId);
    onUpdate();
  };

  const handleImageUpload = async (charId: string, file: File) => {
    await api.uploadCharacterImage(projectId, charId, file);
    onUpdate();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium">
          Персонажи <span className="text-gray-500 text-sm">({characters.length})</span>
        </h3>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors"
        >
          <Plus size={14} />
          Добавить
        </button>
      </div>

      {/* Форма добавления */}
      {showAdd && (
        <div className="mb-4 p-4 bg-surface rounded-lg border border-surface-lighter space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Имя (англ.)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
              autoFocus
            />
            <input
              placeholder="Имя (рус.)"
              value={form.nameRu}
              onChange={(e) => setForm({ ...form, nameRu: e.target.value })}
              className="px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
            />
          </div>
          <input
            placeholder='Одежда (напр. "in the grey hoodie")'
            value={form.clothing}
            onChange={(e) => setForm({ ...form, clothing: e.target.value })}
            className="w-full px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
          />
          <input
            placeholder="Описание персонажа"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
          />
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 px-3 py-1.5 bg-surface-lighter rounded-lg cursor-pointer text-sm text-gray-400 hover:text-white transition-colors">
              <Upload size={14} />
              {imageFile ? imageFile.name : 'Фото референс'}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setImageFile(e.target.files?.[0] || null)}
              />
            </label>
            <div className="flex-1" />
            <button
              onClick={() => { setShowAdd(false); setImageFile(null); }}
              className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleAdd}
              disabled={!form.name.trim() || saving}
              className="px-4 py-1.5 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : 'Добавить'}
            </button>
          </div>
        </div>
      )}

      {/* Список персонажей */}
      {characters.length === 0 ? (
        <p className="text-gray-500 text-sm py-4">Нет персонажей. Добавьте первого.</p>
      ) : (
        <div className="space-y-2">
          {characters.map((char) => (
            <div
              key={char.id}
              className="flex items-center gap-4 p-3 bg-surface rounded-lg border border-surface-lighter"
            >
              {/* Фото */}
              {char.baseImage ? (
                <img
                  src={api.mediaUrl(projectId, char.baseImage)}
                  alt={char.name}
                  className="w-14 h-14 rounded-lg object-cover"
                />
              ) : (
                <label className="w-14 h-14 rounded-lg bg-surface-lighter flex items-center justify-center cursor-pointer hover:bg-gray-600 transition-colors">
                  <User size={20} className="text-gray-500" />
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleImageUpload(char.id, file);
                    }}
                  />
                </label>
              )}

              {/* Инфо */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{char.nameRu || char.name}</span>
                  {char.clothing && (
                    <span className="text-xs text-amber-400">{char.clothing}</span>
                  )}
                </div>
                {char.description && (
                  <p className="text-xs text-gray-500 truncate">{char.description}</p>
                )}
              </div>

              {/* Статус */}
              <span className={`text-xs px-2 py-0.5 rounded ${
                char.status === 'ready' ? 'bg-green-900/40 text-green-400' :
                char.baseImage ? 'bg-yellow-900/40 text-yellow-400' :
                'bg-gray-700/40 text-gray-400'
              }`}>
                {char.status === 'ready' ? 'Готов' : char.baseImage ? 'Есть фото' : 'Нет фото'}
              </span>

              {/* Удалить */}
              <button
                onClick={() => handleDelete(char.id)}
                className="text-gray-500 hover:text-red-400 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
