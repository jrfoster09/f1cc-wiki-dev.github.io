# F1CC Wiki Auto Updating 2026 Results

## After Each Race

1. Fill in results on the Google Sheet (positions, `1*` for fastest lap, quali positions)
2. **File → Download → Comma Separated Values (.csv)**
3. The file must be saved as **`F1CC_2026.csv`** (rename it if needed)
4. Go to the GitHub repo → `data/csv/` folder
5. Drag and drop the CSV file → click **Commit changes**
6. Wait ~2 minutes → site updates automatically ✓

---

## Sheet Format Rules

| What | How to enter |
|------|-------------|
| Finished P1 | `1` |
| Finished P1 with fastest lap | `1*` |
| Did Not Finish | `DNF` |
| Did Not Start / Absent | leave blank or `0` |
| Pole position | put `1` in the **Qualifying** table for that race |

Only **one driver** should have a `*` per race. Fastest lap only counts for points if the driver finishes **inside the top 10** and it's **not a sprint race** — the script handles this automatically.

---

## What the Script Does Automatically

- Reads finishing positions, fastest laps, and qualifying from the CSV
- Calculates points (including FL bonus where applicable)
- Updates `races_2026.json` with full race results
- Re-sorts driver standings by points
- Updates constructor standings
- Commits everything back to the repo

**You never need to touch any JSON files.**

---

## If Something Looks Wrong

1. Check the **Actions** tab on GitHub — click the latest run to see if there's an error
2. If the CSV filename is wrong the Action won't trigger — must be exactly `F1CC_2026.csv`
3. If a driver name in the sheet doesn't exactly match the name in `db.json`, their results will be silently skipped — flag it up so it can be fixed

---

## File Must Be Named

```
F1CC_2026.csv
```

Anything else and the Action won't fire.

