import type { ReactElement } from 'react'
import type { RenderOptions } from '@testing-library/react'
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '../../contexts/ThemeContext'

// Create a custom render function that includes providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string
}

const AllTheProviders = ({
  children,
  route = '/',
}: {
  children: React.ReactNode
  route?: string
}) => {
  // Create a new QueryClient for each test to avoid state pollution
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>{children}</ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const customRender = (ui: ReactElement, { route = '/', ...options }: CustomRenderOptions = {}) => {
  if (route !== '/') {
    window.history.pushState({}, 'Test page', route)
  }

  return render(ui, {
    wrapper: ({ children }) => <AllTheProviders route={route}>{children}</AllTheProviders>,
    ...options,
  })
}

export * from '@testing-library/react'
export { customRender as render }
