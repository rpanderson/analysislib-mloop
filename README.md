<img src="analysislib-mloop-logo.png" height="64" alt="analysislib-mloop" align="right">

# the _labscript suite_ » analysislib-mloop

### Machine-learning online optimisation of 𝘭𝘢𝘣𝘴𝘤𝘳𝘪𝘱𝘵 𝘴𝘶𝘪𝘵𝘦 controlled experiments

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![GitHub](https://img.shields.io/github/license/rpanderson/analysislib-mloop)](https://github.com/rpanderson/analysislib-mloop/raw/master/LICENSE)
[![python: 3.6 | 3.7 | 3.8](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue)](https://python.org)

**analysislib-mloop** implements machine-learning online optimisation of [_labscript suite_](http://labscriptsuite.org) controlled experiments using [M-LOOP](https://m-loop.readthedocs.io).


## Requirements

* [lyse](https://github.com/labscript-suite/lyse) 2.5.0
* [runmanager](https://github.com/labscript-suite/runmanager) 2.5.0+ ([remote-bugfix](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/runmanager/pull-requests/39/page/1))
* [labscript_utils](https://github.com/labscript-suite/labscript_utils) 2.12.4
* [zprocess](https://pypi.org/project/zprocess) 2.13.2
* [M-LOOP](https://m-loop.readthedocs.io/en/latest/install.html) 2.2.0+


## Installation

The following assumes you have a working installation of the [_labscript suite_](https://docs.labscriptsuite.org/en/latest/installation) and [M-LOOP](https://m-loop.readthedocs.io/en/latest/install.html). Please see the installation documentation of these projects if you don't.

Clone this repository in your _labscript suite_ analysislib directory. By default, this is `~/labscript-suite/userlib/analysislib` (`~` is `%USERPROFILE%` on Windows).


## Usage

The following assumes you already have an experiment controlled by the _labscript suite_.

1. **Specify server and port of [runmanager](https://github.com/labscript-suite/runmanager) in your labconfig,** i.e. ensure you have the following entries if their values differ from these defaults:

```ini
[servers]
runmanager = localhost

[ports]
runmanager = 42523
```

2. **Configure optimisation settings in `mloop_config.ini`.** There is a tracked version of this file in the repository. At a bare minimum, you should modify the following:

```ini
[ANALYSIS]
cost_key = ["fake_result", "y"]
maximize = true

[MLOOP]
mloop_params = {"x": {"min": -5.0, "max": 5.0, "start": -2.0} }
```

  * `cost_key`: Column of the lyse dataframe to derive the cost from, specified as a `[routine_name, result_name]` pair. The present cost comes from the most recent value in this column, i.e. `cost = df[cost_key].iloc[-1]`.
  * `maximize`: Whether or not to negate the above value, since M-LOOP will minimize the cost.
  * `mloop_params`: Dictionary of optimisation parameters, specified as (`global_name`, `dict`) pairs, where `dict` is used to create `min_boundary`, `max_boundary`, and `first_params` lists to meet [M-LOOP specifications](https://m-loop.readthedocs.io/en/latest/tutorials.html#parameter-settings).

3. **Load the analysis routine that computes the quantity you want to optimise into [lyse](https://github.com/labscript-suite/lyse).** This routine should update `cost_key` of the lyse dataframe by calling the `save_result` (or its variants) of a `lyse.Run`. For the above parameters, this would be `fake_result.py` containing:

```python
import lyse

run = lyse.Run(lyse.path)

# Your single-shot analysis code goes here

run.save_result('y', your_result)
```

4. **Load `mloop_multishot.py` as an analysis routine in lyse.** Ensure that it runs after the analysis routine that updates `cost_key`, e.g. `fake_result.py` in the above configuration, using the (move routine) up/down buttons.

5. **Begin automated optimisation** by doing one of the following:
    * Press the 'Run multishot analysis' button in lyse.
        + This requires the globals specified in `mloop_params` are active in runmanager; unless you
        + Set `mock = true` in `mloop_config.ini`, which bypasses shot compilation and submission, and generates a fake cost based on the current value of the first optimisation parameter. Each press of 'Run multishot analysis' will elicit another M-LOOP iteration. This is useful for testing your M-LOOP installation and the threading/multiprocessing used in this codebase, as it only requires that lyse be running (and permits you to skip creating the template file and performing steps (1) and (3) above).
    * Press the 'Engage' button in runmanager.
    Either of these will begin an M-LOOP optimisation, with a new sequence of shots being compiled and submitted to [blacs](https://github.com/labscript-suite/blacs) each time a cost value is computed.

6. **Pause optimisation** by pausing the lyse analysis queue or by unchecking (deactivating) the `mloop_multishot.py` in lyse.

7. **Cancel or restart optimisation** by removing `mloop_multishot.py` or by right-clicking on it and selecting 'restart worker process for selected routines'.


### Uncertainties

Uncertaintes in the cost can be specified by saving the uncertainty with a name `'u_' + result_name`. For the example in step (3) above, this can be done as follows:

```python
import lyse

run = lyse.Run(lyse.path)

# Your single-shot analysis code goes here

run.save_result('y', your_result)
run.save_result('u_y', u_your_result)

# ... or:

run.save_results_dict({'y', (your_result, u_your_result)}, uncertainties=True)
```


### Multi-shot cost evaluation

The cost can be the result of multi-shot analysis (requiring more than one shot to evaluate). Suppose you only want to return a cost value after:

  * a certain number of shots (repeats or those in a labscript sequence) have completed, and/or
  * the uncertainty in some multi-shot analysis result is below some threshold.

In such cases, you would include the following in your multi-shot analysis routine:

```python
df = lyse.data()

# Your analysis on the lyse DataFrame goes here

run = lyse.Run(h5_path=df.filepath.iloc[-1])
run.save_result(name='y', value=your_result if your_condition else np.nan)
```

... and set `ignore_bad = true` in the analysis section of `mloop_config.ini`. Shots with `your_condition = False` will be not elicit the cost to be updated, thus postponing the next iteration of optimisation. An example of such a multi-shot routine can be found in fake_result_multishot.py.


### Analysing optimistion results

Since cost evaluation can be based on one or more shots from one or more sequences, additional information is required to analyse a single M-LOOP optimisation session in lyse. Per-shot cost evaluation (e.g. of a single-shot analysis result) results in a single-shot sequence per M-LOOP iteration. For multi-shot cost evaluation, a single M-LOOP iteration might correspond to a single multi-shot sequence, repeated execution of the same shot (same `sequence_index` and `run number`, different `run repeat`), or something else. To keep track of this, we intend to add details of the optimisation session to the sequence attributes (written to each shot file). For the time being, you can keep track of the `mloop_session` and `mloop_iteration` by creating globals with these names in any active group in runmanager. They will be updated during each optimisation, and reset to `None` following the completion of an M-LOOP session. This then permits you to analyse shots from a particular optimisation session as follows:

```python
import lyse

df = lyse.data()
gb = df.groupby('mloop_session')
mloop_session = list(gb.groups.keys())[-1]
subdf = gb.get_group(mloop_session)
```

There's an example of this in plot_mloop_results.py.

M-LOOP itself has [visualisation functions](https://m-loop.readthedocs.io/en/latest/tutorials.html#visualizations) which can be run on the log/archive files it creates.


### Can mloop_multishot.py be a single-shot routine?

The `mloop_multishot.py` script can be loaded as a single-shot analysis routine if `cost_key` derives from another single-shot routine, so long as it runs _after_ that routine.


### Is this implementation limited to M-LOOP?

Despite the name, `mloop_multishot.py` can be used for other automated optimisation and feed-forward. You can run any function the optimisation thread (see below), so long as it conforms to the following specification:

  * Calls `lyse.routine_storage.queue.get()` iteratively.
  * Uses the `cost_dict` returned to modify global variables (which ones and how is up to you) using `runmanager.remote.set_globals()`.
  * Calls `runmanager.remote.engage()` when a new shot or sequence of shots is required to get the next cost (optional).

Feed-forward stabilisation (e.g. of some drifting quantity) could be readily achieved using a single-iteration optimisation session, replacing `main` of mloop_interface.py with, for example:

```python
import lyse
from runmanager.remote import set_globals, engage

def main():
    # cost_dict['cost'] is likely some error signal you are trying to zero
    cost_dict = lyse.routine_storage.queue.get()

    # Your code goes here that determines the next value of a stabilisation parameter
    set_globals('some_global': new_value)

    return
```

If an alternative optimisation library requires something other than `cost_dict` (with keys `cost`, `uncer`, `bad`), you can modify `cost_analysis` accordingly.


## Implementation

We use `lyse.routine_storage` to store:

  * a long-lived thread (`threading.Thread`) to run the main method of `mloop_interface.py` within `mloop_multishot.py`,
  * a queue (`Queue.Queue`) for `mloop_multishot.py`/`mloop_interface.py` to put/get the latest M-LOOP cost dictionary, and
  * (when `mock = true`) a variable `x` for `mloop_interface.py`/`mloop_multishot.py` to set/get, for spoofing an `cost_key` that changes with the current value of the (first) M-LOOP optimisation parameter.

Each time the `mloop_multishot.py` routine runs in lyse, we first check to see if there is an active optimisation by polling the optimisation thread. If it doesn't exist or is not alive, we start a new thread. If there's an optimisation underway, we retrieve the latest cost value from the lyse dataframe (see the `cost_analysis` function) and put it in the `lyse.routine_storage.queue`.

The `LoopInterface` subclass (of `mloop.interface.Interface`) has a method `get_next_cost_dict`, which:

  * requests the next experiment shot(s) be compiled and run using `runmanager.remote.set_global()` and `runmanager.remote.engage()`, and
  * waits for the next cost using a blocking call to `lyse.routine_storage.queue.get()`.

The main method of `mloop_interface.py` follows the trend of the [M-LOOP » Python controlled experiment tutorial](https://m-loop.readthedocs.io/en/latest/tutorials.html#python-controlled-experiment):

  * Instantiate `LoopInterface`, an M-LOOP optmiser interface.
  * Get the current configuration.
  * Create an `mloop.controllers.Controller` instance for the optimiser interface, using the above configuration.
  * Run the `optimize` method of this controller.
  * Return a dictionary of `best_params`, `best_cost`, `best_uncer`, `best_index`.

Shots are compiled by programmatically interacting with the runmanager GUI. The current value of the optimisation parameters used by M-LOOP are reflected in runmanager, and when a given optimisation is complete, the best parameters are entered into runmanager programmatically.


## Roadmap

### Provenance

The original design and implementation occurred during the summer of 2017/2018 by Josh Morris, Ethan Payne, Lincoln Turner, and I, with assistance from Chris Billington and Phil Starkey. In this incarnation, the M-LOOP interface and experiment interface were run as standalone processes in a shell, with communication between these two actors and the analysis interface being done over a ZMQ socket. Experiment scripts were compiled against an otherwise empty 'template' shot file of globals, which was modified in place at each M-LOOP iteration. This required careful execution of the scripts in the right order, and for the M-LOOP interface to be restarted after each optimistion, and was a bit clunky/flaky.

In 2019 we improved this original implementation using a single lyse analysis routine (the skeleton of which was written by Phil Starkey), and [remote control of the runmanager GUI](https://github.com/labscript-suite/runmanager/issues/68). This required the following enhancements and bugfixes to the labscript suite, which Chris Billington (mostly) and I undertook:

  * [lyse PR #61](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/lyse/pull-requests/61): Fix for [#48](https://github.com/labscript-suite/lyse/issues/48): Make analysis_subprocess.py multiprocessing-friendly
  * [lyse PR #62](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/lyse/pull-requests/62): Terminate subprocesses at shutdown
  * [runmanager PR #37](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/runmanager/pull-requests/37): Basic remote control of runmanager
  * [runmanager PR #39](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/runmanager/pull-requests/39): Bugfix of above
  * [labscript_utils PR #78](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/labscript_utils/pull-requests/78): Basic remote control of runmanager): Import pywin32 at module-level rather than lazily
  * [labscript PR #81](http://bitbucket-archive.labscriptsuite.org/#!/labscript_suite/labscript/pull-requests/81): Basic remote control of runmanager): Include all package dirs in Modulewatcher whitelist

M-LOOP was written by Michael Hush and is maintained by [M-LOOP contributors](https://m-loop.readthedocs.io/en/latest/contributing.html#contributors).


### Future improvements

  * Validation and error checks (#1).
  * Sequence attributes that record the optimisation details.
  * Generalise this implementation to other algorithmic optimisaiton libraries.


### Contributing

If you are an existing _labscript suite_ user, please test this out on your experiment! Report bugs, request new functionality, and submit pull requests using the [issue tracker](https://github.com/rpanderson/analysislib-mloop/issues) for this project.

If you'd like to implement machine-learning online optimisation on your shot-based, hardware-timed experiment, please consider deploying the _labscript suite_ and M-LOOP (or another machine learning library, by adapting this extension).
