import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export function Radio() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate('/playlists?kind=dynamic_rules', { replace: true });
  }, [navigate]);
  return null;
}
