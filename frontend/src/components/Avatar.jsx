import { Avatar as MuiAvatar } from "@mui/material";

export default function Avatar({ avatarProps = {}, children }) {
  return <MuiAvatar {...avatarProps}>{children}</MuiAvatar>;
}
