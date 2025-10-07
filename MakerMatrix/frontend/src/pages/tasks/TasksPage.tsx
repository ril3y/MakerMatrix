import { motion } from 'framer-motion'
import { Activity } from 'lucide-react'
import TasksManagement from '@/components/tasks/TasksManagement'

const TasksPage = () => {
  return (
    <div className="max-w-screen-2xl space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Activity className="w-6 h-6" />
            Background Tasks
          </h1>
          <p className="text-secondary mt-1">Monitor and manage background tasks and processes</p>
        </div>
      </motion.div>

      {/* Tasks Management Component */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <TasksManagement />
      </motion.div>
    </div>
  )
}

export default TasksPage
