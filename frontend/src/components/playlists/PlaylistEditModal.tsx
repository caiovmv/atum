import { useState } from 'react';
import { BottomSheet } from '../BottomSheet';
import { Input, Textarea } from '../Input';

interface EditModalCoverPreviewProps {
  playlistId: number;
  hasCustomCover: boolean;
  onCoverUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

function EditModalCoverPreview({ playlistId, hasCustomCover, onCoverUpload }: EditModalCoverPreviewProps) {
  const [showPlaceholder, setShowPlaceholder] = useState(false);
  if (showPlaceholder) {
    return (
      <>
        <span className="pd-edit-cover-placeholder">Sem capa</span>
        <label className="atum-btn atum-btn-primary pd-edit-cover-btn">
          <input type="file" accept="image/*" onChange={onCoverUpload} style={{ display: 'none' }} />
          Adicionar
        </label>
      </>
    );
  }
  return (
    <>
      <img
        src={`/api/playlists/${playlistId}/cover`}
        alt=""
        className="pd-edit-cover-preview"
        onError={() => setShowPlaceholder(true)}
      />
      <label className="atum-btn atum-btn-primary pd-edit-cover-btn">
        <input type="file" accept="image/*" onChange={onCoverUpload} style={{ display: 'none' }} />
        {hasCustomCover ? 'Trocar' : 'Definir manualmente'}
      </label>
    </>
  );
}

interface PlaylistEditModalProps {
  open: boolean;
  onClose: () => void;
  editName: string;
  setEditName: (v: string) => void;
  editDescription: string;
  setEditDescription: (v: string) => void;
  editPrompt: string;
  setEditPrompt: (v: string) => void;
  playlistId: number;
  hasCustomCover: boolean;
  onCoverUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSave: () => void;
  isDynamicAI: boolean;
}

export function PlaylistEditModal({
  open,
  onClose,
  editName,
  setEditName,
  editDescription,
  setEditDescription,
  editPrompt,
  setEditPrompt,
  playlistId,
  hasCustomCover,
  onCoverUpload,
  onSave,
  isDynamicAI,
}: PlaylistEditModalProps) {
  return (
    <BottomSheet open={open} title="Editar coleção" onClose={onClose} showCloseButton>
      <>
        <div className="pd-edit-field">
          <label>Nome</label>
          <Input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
        </div>
        <div className="pd-edit-field">
          <label>Descrição</label>
          <Textarea
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            rows={2}
          />
        </div>
        {isDynamicAI && (
          <div className="pd-edit-field">
            <label>Prompt (AI Mix)</label>
            <Textarea
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              rows={3}
              placeholder="Ex: As 20 músicas mais populares do artista X"
            />
          </div>
        )}
        <div className="pd-edit-field">
          <label>Capa</label>
          <div className="pd-edit-cover">
            <EditModalCoverPreview
              playlistId={playlistId}
              hasCustomCover={hasCustomCover}
              onCoverUpload={onCoverUpload}
            />
          </div>
        </div>
        <div className="pd-edit-actions">
          <button type="button" className="atum-btn atum-btn-primary" onClick={onSave}>
            Salvar
          </button>
          <button type="button" className="atum-btn" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </>
    </BottomSheet>
  );
}
