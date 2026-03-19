import { Toggle, Field } from './SettingsForm';
import { Select } from '../Input';

interface GeneralSectionProps {
  val: (key: string) => string;
  set: (key: string, value: unknown) => void;
  boolVal: (key: string) => boolean;
}

export function GeneralSection({ val, set, boolVal }: GeneralSectionProps) {
  return (
    <>
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Geral</h2>
        <div className="atum-settings-group">
          <Field
            label="Pasta de Música"
            hint="Caminho da pasta principal de música (LIBRARY_MUSIC_PATH)"
            value={val('library_music_path')}
            onChange={(v) => set('library_music_path', v)}
            placeholder="D:\Library\Music"
          />
          <Field
            label="Pasta de Vídeos"
            hint="Caminho da pasta principal de vídeos (LIBRARY_VIDEOS_PATH)"
            value={val('library_videos_path')}
            onChange={(v) => set('library_videos_path', v)}
            placeholder="D:\Library\Videos"
          />
        </div>
      </section>

      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Organização</h2>
        <div className="atum-settings-group">
          <Toggle
            label="Pós-processamento automático"
            hint="Organizar arquivos automaticamente após o download concluir"
            checked={boolVal('post_process_enabled')}
            onChange={(v) => set('post_process_enabled', v)}
          />
          <Field label="Modo de organização" hint="Como os arquivos são organizados após o download">
            <Select
              value={val('organize_mode') || 'in_place'}
              onChange={(e) => set('organize_mode', e.target.value)}
            >
              <option value="in_place">In-place (renomear na mesma pasta)</option>
              <option value="hardlink_to_library">Hardlink para biblioteca separada</option>
              <option value="copy_to_library">Copiar para biblioteca separada</option>
            </Select>
          </Field>
          <Toggle
            label="Naming Plex-compatible"
            hint="Renomear arquivos seguindo convenção do Plex (ex: Movie (2010)/Movie (2010).mkv)"
            checked={boolVal('plex_naming_enabled')}
            onChange={(v) => set('plex_naming_enabled', v)}
          />
          <Toggle
            label="Incluir TMDB ID na pasta"
            hint="Adicionar {tmdb-12345} no nome da pasta para matching preciso"
            checked={boolVal('include_tmdb_id_in_folder')}
            onChange={(v) => set('include_tmdb_id_in_folder', v)}
          />
          <Toggle
            label="Incluir IMDB ID na pasta"
            hint="Adicionar {imdb-tt0137523} no nome da pasta"
            checked={boolVal('include_imdb_id_in_folder')}
            onChange={(v) => set('include_imdb_id_in_folder', v)}
          />
          <Toggle
            label="Upgrade automático de qualidade"
            hint="Substituir arquivo quando uma versão de melhor qualidade é baixada"
            checked={boolVal('auto_upgrade_quality')}
            onChange={(v) => set('auto_upgrade_quality', v)}
          />
        </div>
      </section>

      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Metadados de Áudio</h2>
        <div className="atum-settings-group">
          <Toggle
            label="Escrever metadados nos arquivos"
            hint="Ao editar metadados na biblioteca, salvar também nas tags do arquivo (ID3, Vorbis, etc.)"
            checked={boolVal('write_audio_metadata')}
            onChange={(v) => set('write_audio_metadata', v)}
          />
          <Toggle
            label="Embutir artwork nos arquivos"
            hint="Salvar a capa encontrada como tag de imagem nos arquivos de áudio"
            checked={boolVal('embed_cover_in_audio')}
            onChange={(v) => set('embed_cover_in_audio', v)}
          />
        </div>
      </section>
    </>
  );
}
