import { IoHeart, IoTrophy, IoMusicalNotes, IoRadio, IoSparkles } from 'react-icons/io5';

export function getPlaylistIcon(kind?: string, systemKind?: string) {
  if (systemKind === 'favorites') return <IoHeart size={20} className="pd-icon pd-icon--fav" />;
  if (systemKind === 'most_played') return <IoTrophy size={20} className="pd-icon pd-icon--top" />;
  if (kind === 'dynamic_rules') return <IoRadio size={20} className="pd-icon pd-icon--radio" />;
  if (kind === 'dynamic_ai') return <IoSparkles size={20} className="pd-icon pd-icon--ai" />;
  return <IoMusicalNotes size={20} className="pd-icon" />;
}

export function getPlaylistKindLabel(kind: string) {
  if (kind === 'dynamic_rules') return 'Sintonia';
  if (kind === 'dynamic_ai') return 'AI Mix';
  return 'Playlist';
}

export function getCollectionKindLabel(kind?: string, systemKind?: string) {
  if (systemKind === 'favorites') return 'Favoritos';
  if (systemKind === 'most_played') return 'Mais tocadas';
  if (kind === 'dynamic_rules') return 'Sintonia';
  if (kind === 'dynamic_ai') return 'AI Mix';
  return 'Playlist';
}

export function getCollectionIcon(kind?: string, systemKind?: string) {
  if (systemKind === 'favorites') return <IoHeart size={20} className="playlist-card-icon playlist-card-icon--fav" />;
  if (systemKind === 'most_played') return <IoTrophy size={20} className="playlist-card-icon playlist-card-icon--top" />;
  if (kind === 'dynamic_rules') return <IoRadio size={20} className="playlist-card-icon playlist-card-icon--radio" />;
  if (kind === 'dynamic_ai') return <IoSparkles size={20} className="playlist-card-icon playlist-card-icon--ai" />;
  return <IoMusicalNotes size={20} className="playlist-card-icon" />;
}
