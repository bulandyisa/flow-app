import { useState } from 'react';
import { Plus, Trash2, Upload, MapPin, Image } from 'lucide-react';
import { api } from '@/api/client';

interface Angle {
  id: string;
  file: string;
  description: string;
  status: string;
}

interface Location {
  id: string;
  name: string;
  nameRu: string;
  description: string;
  baseImage: string | null;
  angles: Angle[];
  status: string;
}

interface LocationSetupProps {
  projectId: string;
  locations: Location[];
  onUpdate: () => void;
}

export function LocationSetup({ projectId, locations, onUpdate }: LocationSetupProps) {
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: '', nameRu: '', description: '' });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [expandedLoc, setExpandedLoc] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await api.addLocation(projectId, form, imageFile || undefined);
      setForm({ name: '', nameRu: '', description: '' });
      setImageFile(null);
      setShowAdd(false);
      onUpdate();
    } catch (err) {
      alert(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (locId: string) => {
    await api.deleteLocation(projectId, locId);
    onUpdate();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium">
          Локации <span className="text-gray-500 text-sm">({locations.length})</span>
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
              placeholder="Название (англ.)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
              autoFocus
            />
            <input
              placeholder="Название (рус.)"
              value={form.nameRu}
              onChange={(e) => setForm({ ...form, nameRu: e.target.value })}
              className="px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
            />
          </div>
          <input
            placeholder="Описание локации"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
          />
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 px-3 py-1.5 bg-surface-lighter rounded-lg cursor-pointer text-sm text-gray-400 hover:text-white transition-colors">
              <Upload size={14} />
              {imageFile ? imageFile.name : 'Базовое фото (опционально)'}
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

      {/* Список локаций */}
      {locations.length === 0 ? (
        <p className="text-gray-500 text-sm py-4">Нет локаций. Добавьте первую.</p>
      ) : (
        <div className="space-y-2">
          {locations.map((loc) => (
            <div key={loc.id} className="bg-surface rounded-lg border border-surface-lighter overflow-hidden">
              {/* Строка локации */}
              <div
                className="flex items-center gap-4 p-3 cursor-pointer hover:bg-surface-light transition-colors"
                onClick={() => setExpandedLoc(expandedLoc === loc.id ? null : loc.id)}
              >
                {/* Фото */}
                {loc.baseImage ? (
                  <img
                    src={api.mediaUrl(projectId, loc.baseImage)}
                    alt={loc.name}
                    className="w-20 h-14 rounded-lg object-cover"
                  />
                ) : (
                  <div className="w-20 h-14 rounded-lg bg-surface-lighter flex items-center justify-center">
                    <MapPin size={20} className="text-gray-500" />
                  </div>
                )}

                {/* Инфо */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{loc.nameRu || loc.name}</div>
                  {loc.description && (
                    <p className="text-xs text-gray-500 truncate">{loc.description}</p>
                  )}
                </div>

                {/* Ракурсы */}
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Image size={12} />
                  <span>{loc.angles.length} ракурсов</span>
                </div>

                {/* Статус */}
                <span className={`text-xs px-2 py-0.5 rounded ${
                  loc.status === 'ready' ? 'bg-green-900/40 text-green-400' :
                  loc.angles.length >= 15 ? 'bg-blue-900/40 text-blue-400' :
                  loc.baseImage ? 'bg-yellow-900/40 text-yellow-400' :
                  'bg-gray-700/40 text-gray-400'
                }`}>
                  {loc.status === 'ready' ? 'Готова' :
                   loc.angles.length >= 15 ? 'Ракурсы готовы' :
                   loc.baseImage ? 'Нужны ракурсы' : 'Нет фото'}
                </span>

                {/* Удалить */}
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(loc.id); }}
                  className="text-gray-500 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              {/* Развёрнутый вид: ракурсы */}
              {expandedLoc === loc.id && (
                <div className="px-3 pb-3 border-t border-surface-lighter">
                  <div className="pt-3">
                    {loc.angles.length === 0 ? (
                      <div className="text-sm text-gray-500 py-2">
                        {loc.baseImage
                          ? 'Ракурсы будут сгенерированы ботом после принятия базового фото.'
                          : 'Сначала загрузите или сгенерируйте базовое фото локации.'}
                      </div>
                    ) : (
                      <div className="grid grid-cols-5 gap-2">
                        {loc.angles.map((angle) => (
                          <div key={angle.id} className="text-center">
                            <img
                              src={api.mediaUrl(projectId, angle.file)}
                              alt={angle.description}
                              className="w-full aspect-video rounded object-cover"
                              loading="lazy"
                            />
                            <span className="text-xs text-gray-500 mt-1 block truncate">
                              {angle.description}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
