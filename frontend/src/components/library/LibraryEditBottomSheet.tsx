import { BottomSheet } from '../BottomSheet';
import type { LibraryItem } from '../../types/library';

interface EditForm {
  name: string;
  year: string;
  artist: string;
  album: string;
  genre: string;
  tagsStr: string;
}

interface LibraryEditBottomSheetProps {
  open: boolean;
  onClose: () => void;
  editingItem: LibraryItem | null;
  editForm: EditForm;
  setEditForm: React.Dispatch<React.SetStateAction<EditForm>>;
  onSave: () => void;
  saving: boolean;
  contentType: 'music' | 'concerts' | 'movies' | 'tv';
}

export function LibraryEditBottomSheet({
  open,
  onClose,
  editingItem,
  editForm,
  setEditForm,
  onSave,
  saving,
  contentType,
}: LibraryEditBottomSheetProps) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Editar metadados">
      {editingItem && (
        <>
          <div className="atum-library-modal-form">
            <label>
              Nome
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
              />
            </label>
            <label>
              Ano
              <input
                type="text"
                inputMode="numeric"
                value={editForm.year}
                onChange={(e) => setEditForm((f) => ({ ...f, year: e.target.value }))}
              />
            </label>
            {(editingItem.content_type === 'music' || editingItem.content_type === 'concerts' || contentType === 'music' || contentType === 'concerts') && (
              <>
                <label>
                  Artista
                  <input
                    type="text"
                    value={editForm.artist}
                    onChange={(e) => setEditForm((f) => ({ ...f, artist: e.target.value }))}
                  />
                </label>
                <label>
                  Álbum
                  <input
                    type="text"
                    value={editForm.album}
                    onChange={(e) => setEditForm((f) => ({ ...f, album: e.target.value }))}
                  />
                </label>
              </>
            )}
            <label>
              Gênero
              <input
                type="text"
                value={editForm.genre}
                onChange={(e) => setEditForm((f) => ({ ...f, genre: e.target.value }))}
              />
            </label>
            <label>
              Tags (separadas por vírgula)
              <input
                type="text"
                value={editForm.tagsStr}
                onChange={(e) => setEditForm((f) => ({ ...f, tagsStr: e.target.value }))}
                placeholder="ex: rock, ao-vivo"
              />
            </label>
          </div>
          <div className="atum-library-modal-actions">
            <button type="button" className="atum-btn" onClick={onClose}>
              Cancelar
            </button>
            <button type="button" className="atum-btn atum-btn-primary" onClick={onSave} disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </>
      )}
    </BottomSheet>
  );
}
