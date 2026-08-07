import { Select as MuiSelect, InputLabel, MenuItem, FormControl } from "@mui/material";

export default function Select({ selectProps = {}, inputLabelProps = {}, options = [] }) {
  return (
    <FormControl fullWidth>
      {inputLabelProps && <InputLabel {...inputLabelProps}>{inputLabelProps.children}</InputLabel>}
      <MuiSelect {...selectProps}>
        {options.map((opt) => (
          <MenuItem key={opt.value} value={opt.value}>
            {opt.label}
          </MenuItem>
        ))}
      </MuiSelect>
    </FormControl>
  );
}
