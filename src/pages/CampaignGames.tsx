import {Navigate} from 'react-router-dom';

/** The library always uses the active child in the existing account flow. */
export default function CampaignGames() {
  return <Navigate to="/chat?scene=room&tab=home&games=1" replace />;
}
