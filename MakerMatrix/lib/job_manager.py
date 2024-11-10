from collections import namedtuple

Job = namedtuple("Job", ["parser", "client_id"])


class JobManager:
    def __init__(self):
        self.jobs_queue = []

    def create_job(self, parser, client_id):
        # Create a job with the parser and client_id
        job = Job(parser, client_id)
        self.jobs_queue.append(job)

    def get_job(self, client_id, part_number):
        # Retrieve a job based on client_id and part_number
        return next((job for job in self.jobs_queue if
                     job.client_id == client_id and job.parser.part.part_number == part_number), None)

    def remove_job(self, job):
        # Remove a job from the queue
        if job in self.jobs_queue:
            self.jobs_queue.remove(job)

    def clear_jobs_for_client(self, client_id):
        # Clear all jobs associated with a disconnected client
        self.jobs_queue = [job for job in self.jobs_queue if job.client_id != client_id]
