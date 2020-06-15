import lyse
import numpy as np
from fake_result import fake_result

df = lyse.data()

# Your analysis on the lyse DataFrame goes here
if len(df):
    ix = df.iloc[-1].name[0]
    subdf = df.loc[ix]
    your_result = fake_result(subdf.x.mean())
    your_condition = len(subdf) > 3

    # Save sequence analysis result in latest run
    run = lyse.Run(h5_path=df.filepath.iloc[-1])
    run.save_result(name='y', value=your_result if your_condition else np.nan)
