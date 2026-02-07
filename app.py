#!/usr/bin/env python3
from cdk.resume_processor import ResumeProcessorWorkflow
import aws_cdk as cdk

app = cdk.App()
ResumeProcessorWorkflow(app, "ResumeProcessorWorkflow")
app.synth()
