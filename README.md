## Description

This repository implements machine-learning online optimisation of [labscript](https://labscriptsuite.org) controlled experiments using [M-LOOP](https://m-loop.readthedocs.io).

## Requirements

* [lyse](https://bitbucket.org/labscript_suite/lyse) 2.5.0
* [labscript_utils](https://bitbucket.org/labscript_suite/labscript_utils) 2.12.4
* [zprocess](https://pypi.org/project/zprocess) 2.13.1
* [M-LOOP](https://m-loop.readthedocs.io/en/latest/install.html) 2.2.0+

## Usage

The following assumes you already have an experiment controlled by the labscript suite. 

1. **Specify server and port of [blacs](https://bitbucket.org/labscript_suite/blacs) in your labconfig,** i.e. ensure you have the following entries with appropriate values:

        [servers]
        blacs = localhost
    
        [ports]
        blacs = 42517

2. **Configure optimisation settings in `mloop_config.ini`.** There is a tracked version of this file in the repository. At a bare minimum, you will need to modify the following:

        [COMPILATION]
        labscript_file = "mloop_test.py"
        template_folder = "C:\\Experiments\\example_experiment\\mloop_test"
        template_file = "template.h5"
        
        [ANALYSIS]
        opt_param = ["fake_result", "y"]
        
        [MLOOP]
        mloop_params = {"x": {"min": -5.0, "max": 5.0, "start": -2.0, "group": "some_group"} }
        
    * Compilation
        * `labscript_file`: filename of experiment script you wish to perform optimisation with. This is a relative path under `labscriptlib` (defined in your labconfig).
        * `template_folder`: where to store the template shot file that is used to compile the above experiment script against.
        * `template_file`: filename of template shot, in above folder. _Note_: If `autogenerate_template = true` (see below), this need not exist.
    * Analysis
        * `opt_param`: Column of the lyse dataframe to derive the cost from, specified as a (routine name, result name) tuple. The present cost is the most recent value in this column, negated, i.e. `cost = -1.0 * df[opt_param].iloc[-1]`, where `df = lyse.data()`.
    * M-LOOP
        * `mloop_params`: Dictionary of optimisation parameters, specified as (`global_name`, `dict`) pairs, where `dict` meets the specifications of M-LOOP, plus an additional item specifying the globals group of each optimisation parameter. In the above example, `template.h5` contains the group `globals/some_group` with an attribute named `x`.

3. **Load the analysis routine that computes the quantity you want to optimise into [lyse](https://bitbucket.org/labscript_suite/lyse).** This routine should update `opt_param` of the lyse dataframe by calling the `save_result` (or its variants) of a `lyse.Run`. For the above parameters, this would be `fake_result.py` containing:

        run = lyse.Run(lyse.path)
        
        # Your single-shot analysis code goes here
        
        run.save_result('y', your_result)

4. **Load `mloop_multishot.py` as an analysis routine in lyse.** Ensure that it runs after the analysis routine that updates `opt_param`, e.g. `fake_result.py` in the above configuration, using the (move routine) up/down buttons.

5. **Begin automated optimisation** by doing one of the following:
    * Press the 'Run multishot analysis' button in lyse.
        + This requires the template shot file exists and contains the globals specified in `mloop_params`; unless you
        + Set `mock = true` in `mloop_config.ini`, which bypasses shot compilation and submission, and generates a fake cost based on the current value of the first optimisation parameter. Each press of 'Run multishot analysis' will elicit another M-LOOP iteration. This is useful for testing your M-LOOP installation and the threading/multiprocessing used in this codebase, as it only requires that lyse be running (and permits you to skip creating the template file and performing steps (1) and (3) above).
    * Set `autogenerate_template = true` in `mloop_config.ini` and run a shot using [runmanager](https://bitbucket.ord/runmanager). This will generate a new template file at the start of each optimisation, making a back up of the previous template.    
    Either of these will begin an M-LOOP optimisation, with a new shot being compiled and submitted to [blacs](https://bitbucket.ord/blacs) each time a cost value is computed.

6. **Pause optimisation** by pausing the lyse analysis queue or by unchecking (deactivating) the `mloop_multishot.py` in lyse.

7. **Cancel or restart optimisation** by removing `mloop_multishot.py` or by right-clicking on it and selecting 'restart worker process for selected routines'.


### Notes

The `mloop_multishot.py` script can be loaded as a single-shot analysis routine if `opt_param` derives from another single-shot routine, so long as it runs _after_ that routine.

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

... and set `ignore_nans = true` in the analysis section of `mloop_config.ini`. This will pass `None` to M-LOOP, which postpones the next iteration of optimisation.

## Implementation

We use `lyse.routine_storage` to store:

* a long-lived thread (`threading.Thread`) to run the main method of `mloop_interface.py` within `mloop_multishot.py`,
* a queue (`Queue.Queue`) for `mloop_multishot.py`/`mloop_interface.py` to put/get the latest M-LOOP cost dictionary, and
* (when `mock = true`) a variable `x` for `mloop_interface.py`/`mloop_multishot.py` to set/get, for spoofing an `opt_param` that changes with the current value of the (first) M-LOOP optimisation parameter.

Each time the `mloop_multishot.py` routine runs in lyse, we first check to see if there is an active optimisation by polling the optimisation thread. If it doesn't exist or is not alive, we start a new thread. If there's an optimisation underway, we retrieve the latest cost value from the lyse dataframe (see the `cost_analysis` function) and put it in the `lyse.routine_storage.queue`.

The `LoopInterface` subclass (of `mloop.interface.Interface`) has a method `get_next_cost_dict`, which:

* requests the next experiment shot be compiled, run, and returned to lyse by calling `compile_and_run_shot` function of `mloop_experiment_interface.py`, and
* waits for the next cost using a blocking call to `lyse.routine_storage.queue.get()`.

The main method of `mloop_interface.py` follows the trend of the [M-LOOP >> Python controlled experiment tutorial](https://m-loop.readthedocs.io/en/latest/tutorials.html#python-controlled-experiment):

* Instantiate `LoopInterface`, an M-LOOP optmiser interface.
* Get the current configuration.
* Create an `mloop.controllers.Controller` instance for the optimiser interface, using the above configuration.
* Run the `optimize` method of this controller.
* Return a dictionary of `best_params`, `best_cost`, `best_uncer`, `best_index`.
 
The `compile_and_run_shot` function of `mloop_experiment_interface.py` does what it says on the packet:

* compiles a shot using `runmanager.compile_labscript_with_globals_files_async`, and
* submits this to blacs using `zprocess.zmq_get`.
   
## Roadmap

### Provenance

The original design and implementation occurred during the summer of 2017/2018 by Josh Morris, Ethan Payne, Lincoln Turner, and I, with assistance from Chris Billington and Phil Starkey. In this incarnation, the M-LOOP interface and experiment interface were run as standalone processes in a shell, with communication between these two actors and the analysis interface being done over a ZMQ socket. This required careful execution of the scripts in the right order, and for the M-LOOP interface to be restarted after each optimistion, and was a bit clunky/flaky.

In 2019 Lincoln Turner and I supervised student projects on improving this original implementation using a single lyse analysis routine, the skeleton of which was written by Phil Starkey. This refactoring required the following enhancements and bugfixes to the labscript suite, which Chris Billington (mostly) and I undertook:

* [lyse PR #61](https://bitbucket.org/labscript_suite/lyse/pull-requests/61): Fix for [#48](https://bitbucket.org/labscript_suite/lyse/issues/48): Make analysis_subprocess.py multiprocessing-friendly
* [lyse PR #62](https://bitbucket.org/labscript_suite/lyse/pull-requests/62): Terminate subprocesses at shutdown.
* [labscript_utils PR #78](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/78): Import pywin32 at module-level rather than lazily
   
### Future improvements 

Experiment shot compilation, following runmanager [UI scripting](https://bitbucket.org/labscript_suite/runmanager/issues/68/ui-scripting), so that shots can be compiled and run by programmatically interacting with the GUI rather than using the existing set of limited runmanager library calls. This will have several advantages, including:

* No need for a template shot file.
* No need to specify the globals group of each optimisation parameters.
* No need to replicate code that defines `sequence_attrs`, `shot_output_dir`, and `filename_prefix` in `mloop_experiment_interface.py`.
* No need to explicitly send shot file(s) to blacs: runmanager will do this automatically.
* The current value of the optimisation parameters used by M-LOOP will be reflected in the runmanager GUI.
* Better support for compiling and submitting a sequence of shots for each M-LOOP iteration.
   
### Contributing

If you are an existing labscript user, please test this out on your experiment! Report bugs, request new functionality, and submit pull requests using the BitBucket page for this repository.

If you'd like to implement machine-learning online optimisation on your shot-based, hardware-timed experiment, please consider deploying the labscript suite and M-LOOP.