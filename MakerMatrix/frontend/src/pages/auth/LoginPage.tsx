import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { LogIn, Eye, EyeOff, AlertCircle, UserRound } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import type { LoginRequest } from '@/types/auth'

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

const LoginPage = () => {
  const { login, guestLogin, error, clearError } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isGuestLoading, setIsGuestLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    clearError()

    try {
      await login(data as LoginRequest)
      // Force a page reload to ensure proper state initialization
      window.location.href = '/dashboard'
    } catch (_error) {
      setIsLoading(false)
      // Error is handled in the store
    }
  }

  const handleGuestLogin = async () => {
    setIsGuestLoading(true)
    clearError()

    try {
      await guestLogin()
      // Force a page reload to ensure proper state initialization
      window.location.href = '/dashboard'
    } catch (_error) {
      setIsGuestLoading(false)
      // Error is handled in the store
    }
  }

  return (
    <motion.div
      className="w-full max-w-md"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-primary mb-2">Welcome Back</h1>
        <p className="text-secondary">Sign in to access your MakerMatrix inventory</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-start gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-400">{error}</p>
          </motion.div>
        )}

        <div>
          <label htmlFor="username" className="block text-sm font-medium text-secondary mb-2">
            Username
          </label>
          <input
            {...register('username')}
            type="text"
            id="username"
            className="input w-full"
            placeholder="Enter your username"
            autoComplete="username"
          />
          {errors.username && (
            <p className="text-red-400 text-sm mt-1">{errors.username.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-secondary mb-2">
            Password
          </label>
          <div className="relative">
            <input
              {...register('password')}
              type={showPassword ? 'text' : 'password'}
              id="password"
              className="input w-full pr-10"
              placeholder="Enter your password"
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted hover:text-secondary transition-colors"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          {errors.password && (
            <p className="text-red-400 text-sm mt-1">{errors.password.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading || isGuestLoading}
          className="btn btn-primary w-full flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <motion.div
                className="w-5 h-5 border-2 border-bg-primary/30 border-t-bg-primary rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
              Signing in...
            </>
          ) : (
            <>
              <LogIn className="w-5 h-5" />
              Sign In
            </>
          )}
        </button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-bg-primary px-2 text-muted">Or</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleGuestLogin}
          disabled={isLoading || isGuestLoading}
          className="btn btn-secondary w-full flex items-center justify-center gap-2"
        >
          {isGuestLoading ? (
            <>
              <motion.div
                className="w-5 h-5 border-2 border-secondary/30 border-t-secondary rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
              Loading guest access...
            </>
          ) : (
            <>
              <UserRound className="w-5 h-5" />
              View as Guest
            </>
          )}
        </button>
      </form>
    </motion.div>
  )
}

export default LoginPage
