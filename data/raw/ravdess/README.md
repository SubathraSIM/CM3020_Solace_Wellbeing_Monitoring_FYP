---
license: mit
---

# RAVDESS

This is an audio classification dataset for **Emotion Recognition**.

**Classes = 8  &nbsp;&nbsp;,&nbsp;&nbsp;  Split = Train-Test** 


## Structure
- `audios` folder contains audio files.
- `train.csv` for training split and `test.csv` for the testing split.

## Download
```python
import os
import huggingface_hub
audio_datasets_path = "DATASET_PATH/Audio-Datasets"
if not os.path.exists(audio_datasets_path): print(f"Given {audio_datasets_path=} does not exist. Specify a valid path ending with 'Audio-Datasets' folder.")
huggingface_hub.snapshot_download(repo_id="MahiA/RAVDESS", repo_type="dataset", local_dir=os.path.join(audio_datasets_path, "RAVDESS"))
```


## Acknowledgment
This dataset is a slightly processed/restructured version of data originally released by [Source](https://zenodo.org/records/1188976#.YFZuJ0j7SL8).<br>
Please refer to the respective source for their licensing details and any additional information.



## Contact
For questions or feedback, please create an issue.

