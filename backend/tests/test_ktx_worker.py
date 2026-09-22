from ktx_worker import run_scheduler


def test_scheduler_checks_immediately_then_draws_a_new_delay_each_time():
    events = []
    delays = iter((120, 300))
    checks = 0

    def check():
        nonlocal checks
        checks += 1
        events.append('check')

    def wait(seconds):
        events.append(('wait', seconds))

    run_scheduler(check, wait=wait,
                  random_delay=lambda start, end: next(delays),
                  should_stop=lambda: checks == 2)

    assert events == ['check', ('wait', 120), 'check', ('wait', 300)]


def test_scheduler_waits_after_a_failed_check():
    events = []

    def check():
        events.append('check')
        raise RuntimeError('provider unavailable')

    def wait(seconds):
        events.append(('wait', seconds))

    run_scheduler(check, wait=wait,
                  random_delay=lambda start, end: 180,
                  should_stop=lambda: len(events) == 2)

    assert events == ['check', ('wait', 180)]
