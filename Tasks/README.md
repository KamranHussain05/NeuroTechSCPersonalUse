# Tasks for Recording Neural Data

## Radial 8 / Center Out Task
Basic cursor control calibration task where you move the cursor out from the center to one of the 8 directions indicated by dots. 
When the center dot disappears, that is a cue for you to move your cursor to the dot that is green from the center of the circle.

## Grid Task
Squares in a grid randomly are turned green indicating you to move to that grid and click down. See 
[https://neuralink.com/webgrid/]([url](https://neuralink.com/webgrid/)). This task can be used for calibrating cursor control on 
a daily basis, evaluating the bit-rate (performance) of our cursor decoder, or training a complicated cursor control paradigm.

## Whole-hand Diagnostic Block
A simple visual cue diagnostic block that instructs the user to perform the following tasks while wearing the wrist band. This is defining imagery for
the entire hand not the fingers.
- Do Nothing
- Squeeze fist
- Flex hand
- Wrist up
- Wrist Down
- Wrist Left
- Wrist Right
- Rotate wrist clockwise
- Rotate wrist counter clockwise

## Finger SNR Diagnostic
A diagnostic block to understand the SNR of each of the fingers and determine if they are decodable or not. The user starts with their
hand closed in a light fist. The cues are as follows:
- do nothing
- extend thumb
- extend pointer finger
- extend middle finger
- extend ring finger
- extend pinky finger
- extend all
- squeeze fist

## Task Design
Each of these tasks should save the data into a .mat file. This is a tabular structure file where each "trial" of neural activity is saved along 
with the cue that was presented. The presented cue will serve as the ground truth for training our decoding machine learning models. One "column" of
the mat file will contain the neural data (labeled neural_data) and another column will record the label for that data (i.e. the presented cue). 
An additional column will include a dictionary of metadata including the date, time, length of session, metadata. Another column will include the 
recording parameters and a column for gyroscope data during each trial. 
