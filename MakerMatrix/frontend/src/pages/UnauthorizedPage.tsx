import { motion } from 'framer-motion'
import { ShieldOff, ArrowLeft, Lock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const UnauthorizedPage = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md text-center"
      >
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ duration: 0.5, type: "spring" }}
          className="inline-flex items-center justify-center w-24 h-24 bg-destructive/10 rounded-full mb-6"
        >
          <ShieldOff className="w-12 h-12 text-destructive" />
        </motion.div>

        <h1 className="text-4xl font-bold text-primary mb-4">
          403 - Access Denied
        </h1>
        
        <p className="text-lg text-secondary mb-8">
          You don't have permission to access this resource in the Battle With Bytes system.
        </p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-bg-secondary rounded-lg p-6 mb-8"
        >
          <div className="flex items-center justify-center gap-3 text-secondary">
            <Lock className="w-5 h-5" />
            <p className="text-sm">
              This area requires elevated permissions. Please contact your system administrator
              if you believe you should have access.
            </p>
          </div>
        </motion.div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Go Back
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary"
          >
            Return to Dashboard
          </button>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-12 text-sm text-muted"
        >
          <p>Error Code: BWB-403</p>
          <p className="mt-1">
            If you continue to experience issues, please reference this code when contacting support.
          </p>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default UnauthorizedPage