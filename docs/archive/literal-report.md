# Literal report

`make literal-report` writes `build/literal_report.json` and prints the largest
repeated literals across Spectrum C sources and overlay/Spectrum ASM.

Use it before token-stream or string-table work. The report is an inventory, not
a size claim: every tokenization attempt still needs `make size-report` or
`make size-check` measurement.
