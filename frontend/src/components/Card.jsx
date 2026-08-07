import { Card as MuiCard, CardContent as MuiCardContent } from "@mui/material";

export default function Card({ cardProps = {}, cardContentProps = {}, children }) {
  return (
    <MuiCard {...cardProps}>
      <MuiCardContent {...cardContentProps}>
        {children}
      </MuiCardContent>
    </MuiCard>
  );
}
