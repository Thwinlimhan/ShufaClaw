# Test file for workflow engine
# Run this to verify the workflow engine is working

import asyncio
from crypto_agent.core.workflow_engine import workflow_engine, Workflow, WorkflowStep

print("🧪 Testing Workflow Engine...\n")

# Test 1: Check built-in workflows are registered
print("1️⃣ Checking built-in workflows...")
workflows = workflow_engine.get_workflow_status()
print(f"   Found {len(workflows)} workflows:")
for wf in workflows:
    print(f"   - {wf['name']}: {wf['description']}")

if len(workflows) == 4:
    print("   ✅ All 4 built-in workflows registered!\n")
else:
    print(f"   ⚠️ Expected 4 workflows, found {len(workflows)}\n")

# Test 2: Create a simple test workflow
print("2️⃣ Creating a test workflow...")

async def test_step_1(context, **params):
    """Test step that returns a value."""
    print("   Executing test step 1...")
    return {"message": "Step 1 complete", "value": 42}

async def test_step_2(context, **params):
    """Test step that uses previous result."""
    print("   Executing test step 2...")
    prev_result = context.get('step_1_result')
    if prev_result:
        print(f"   Previous step returned: {prev_result}")
    return {"message": "Step 2 complete", "doubled": prev_result.get('value', 0) * 2}

test_workflow = Workflow(
    name="test_workflow",
    description="Simple test workflow",
    steps=[
        WorkflowStep("Test Step 1", test_step_1),
        WorkflowStep("Test Step 2", test_step_2)
    ]
)

workflow_engine.register_workflow(test_workflow)
print("   ✅ Test workflow created!\n")

# Test 3: Run the test workflow
print("3️⃣ Running test workflow...")

async def run_test():
    result = await workflow_engine.run_workflow("test_workflow")
    return result

result = asyncio.run(run_test())

print(f"   Status: {result['status']}")
print(f"   Steps completed: {result['steps_completed']}/{result['total_steps']}")
print(f"   Duration: {result['duration']:.2f}s")

if result['status'] == 'success':
    print("   ✅ Test workflow executed successfully!\n")
else:
    print(f"   ❌ Test workflow failed: {result.get('error')}\n")

# Test 4: Check workflow status
print("4️⃣ Checking workflow status...")
status = workflow_engine.get_workflow_status()
test_wf_status = next((wf for wf in status if wf['name'] == 'test_workflow'), None)

if test_wf_status:
    print(f"   Name: {test_wf_status['name']}")
    print(f"   Description: {test_wf_status['description']}")
    print(f"   Last status: {test_wf_status['last_status']}")
    print("   ✅ Workflow status tracking works!\n")
else:
    print("   ⚠️ Could not find test workflow in status\n")

# Test 5: Check scheduling
print("5️⃣ Checking scheduled workflows...")
scheduled = workflow_engine.scheduled_workflows
print(f"   Found {len(scheduled)} scheduled workflows:")
for name, info in scheduled.items():
    print(f"   - {name}: {info['schedule']}")
    if info.get('next_run'):
        print(f"     Next run: {info['next_run'].strftime('%Y-%m-%d %H:%M')}")

if len(scheduled) >= 4:
    print("   ✅ Scheduling system works!\n")
else:
    print(f"   ⚠️ Expected at least 4 scheduled workflows, found {len(scheduled)}\n")

print("="*50)
print("✅ WORKFLOW ENGINE TEST COMPLETE!")
print("="*50)
print("\nNext steps:")
print("1. Initialize database tables (see WORKFLOW_ENGINE_GUIDE.md)")
print("2. Register command handlers in main.py")
print("3. Set up the scheduler")
print("4. Test with /workflows command in Telegram")
