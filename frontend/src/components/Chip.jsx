import { Chip as MuiChip } from "@mui/material";

export default function Chip({ chipProps = {} }) {
  return <MuiChip {...chipProps} />;
}
