# Best Practices Reference — React, JavaScript, and Web Development

**Purpose:** Reference document for React and JavaScript best practices  
**Use:** Consult before writing code, during code review, or when uncertain  
**Time:** Use as needed throughout development  
**Related:** All other prompts reference this guide

---

## JavaScript Best Practices

### Variables & Constants

```javascript
// ✅ GOOD: Use const by default
const config = { /* ... */ };
const MAX_RETRIES = 3;

// ✅ GOOD: Use let for values that change
let currentRetry = 0;

// ❌ BAD: Avoid var
var oldStyle = 'outdated';

// ❌ BAD: Avoid magic numbers
setTimeout(() => { /* ... */ }, 5000); // What is 5000?

// ✅ GOOD: Named constants instead
const RETRY_DELAY_MS = 5000;
setTimeout(() => { /* ... */ }, RETRY_DELAY_MS);
```

### Naming Conventions

```javascript
// ✅ GOOD: Descriptive variable names
const userAuthToken = getAuthToken();
const isLoading = true;
const hasError = checkForErrors();

// ❌ BAD: Cryptic names
const u = getAuthToken();
const l = true;
const e = checkForErrors();

// ✅ GOOD: Boolean naming conventions
const isActive = true;
const hasPermission = false;
const canDelete = true;
const shouldRetry = true;

// ✅ GOOD: Function names describe what they do
function getUserById(id) { /* ... */ }
function validateEmail(email) { /* ... */ }
function fetchUserData() { /* ... */ }

// ❌ BAD: Vague function names
function process(x) { /* ... */ }
function do() { /* ... */ }
function update() { /* ... */ }
```

### Async/Await & Error Handling

```javascript
// ✅ GOOD: Use async/await
async function fetchUser(id) {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error('Failed to fetch user');
    return await response.json();
  } catch (error) {
    console.error('Error fetching user:', error);
    throw error; // Re-throw or handle appropriately
  }
}

// ❌ BAD: Callback hell
function fetchUser(id, callback) {
  fetch(`/api/users/${id}`)
    .then(response => response.json())
    .then(data => callback(null, data))
    .catch(error => callback(error));
}

// ❌ BAD: Unhandled promise rejection
fetch('/api/users').then(data => console.log(data));
```

### Destructuring & Modern Syntax

```javascript
// ✅ GOOD: Destructure objects
const { name, email, role } = user;
const { width, height } = dimensions;

// ✅ GOOD: Use template literals
const message = `Hello, ${name}! Your email is ${email}.`;

// ❌ BAD: String concatenation
const message = 'Hello, ' + name + '! Your email is ' + email + '.';

// ✅ GOOD: Use optional chaining
const phone = user?.contact?.phone?.number;

// ❌ BAD: Manual null checks
const phone = user && user.contact && user.contact.phone ? user.contact.phone.number : undefined;

// ✅ GOOD: Use nullish coalescing
const timeout = config.timeout ?? DEFAULT_TIMEOUT;

// ✅ GOOD: Spread operator
const newArray = [...oldArray, newItem];
const newObject = { ...oldObject, updatedField: value };
```

---

## React Best Practices

### Functional Components & Hooks

```javascript
// ✅ GOOD: Functional components with hooks
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch user
    const fetchUser = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        setUser(data);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return null;

  return <div>{user.name}</div>;
}

// ❌ BAD: Class components (older style)
class UserProfile extends React.Component {
  // ... verbose code ...
}
```

### Props Design

```javascript
// ✅ GOOD: Clear, documented props
function Button({ 
  label,           // Text displayed on button
  onClick,         // Called when button is clicked
  disabled = false, // Whether button is disabled
  variant = 'primary' // 'primary' or 'secondary'
}) {
  return (
    <button 
      onClick={onClick}
      disabled={disabled}
      className={`btn btn-${variant}`}
    >
      {label}
    </button>
  );
}

// ✅ GOOD: PropTypes for runtime checking
import PropTypes from 'prop-types';

Button.propTypes = {
  label: PropTypes.string.isRequired,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
  variant: PropTypes.oneOf(['primary', 'secondary'])
};

// ❌ BAD: Too many props
function ComplexComponent({ a, b, c, d, e, f, g, h }) {
  // Hard to understand what these props mean
}

// ✅ GOOD: Group related props in objects
function UserForm({ user, onSubmit, validationRules }) {
  // Clearer structure
}
```

### Hooks Dependencies

```javascript
// ✅ GOOD: Correct dependencies
useEffect(() => {
  fetchUser(userId);
}, [userId]); // Fetch when userId changes

// ✅ GOOD: Cleanup function
useEffect(() => {
  const subscription = subscribe(userId);
  return () => subscription.unsubscribe(); // Cleanup
}, [userId]);

// ❌ BAD: Missing dependencies
useEffect(() => {
  fetchUser(userId); // userId is missing from dependencies!
}, []);

// ❌ BAD: Empty dependencies when effects depend on state
useEffect(() => {
  console.log(count); // count is missing!
}, []);
```

### Component Memoization

```javascript
// ✅ GOOD: Memoize expensive components
const UserCard = React.memo(({ user }) => {
  return <div>{user.name}</div>;
});

// ✅ GOOD: useCallback for stable functions
function UserList({ onSelect }) {
  const handleSelect = useCallback((userId) => {
    onSelect(userId);
  }, [onSelect]); // Only recreate if onSelect changes

  return <div onClick={() => handleSelect(1)}>...</div>;
}

// ✅ GOOD: useMemo for expensive calculations
function UserStats({ user }) {
  const stats = useMemo(() => {
    // Expensive calculation
    return calculateStats(user);
  }, [user]);

  return <div>{stats}</div>;
}

// ❌ BAD: Over-memoizing
const SimpleText = React.memo(({ text }) => <p>{text}</p>); // Not needed
```

### Lists & Keys

```javascript
// ✅ GOOD: Use unique key prop
function UserList({ users }) {
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}

// ❌ BAD: Use array index as key (breaks if list reorders)
function UserList({ users }) {
  return (
    <ul>
      {users.map((user, index) => (
        <li key={index}>{user.name}</li>
      ))}
    </ul>
  );
}
```

### Error Handling

```javascript
// ✅ GOOD: Error Boundary for component errors
class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong</div>;
    }
    return this.props.children;
  }
}

// ✅ GOOD: Try/catch for async errors
async function loadData() {
  try {
    const data = await fetch('/api/data');
    return data;
  } catch (error) {
    console.error('Failed to load data:', error);
    // Handle error appropriately
  }
}
```

---

## Code Organization Best Practices

### File Structure

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.js
│   │   ├── Button.css
│   │   └── Button.test.js
│   ├── Input/
│   │   ├── Input.js
│   │   ├── Input.css
│   │   └── Input.test.js
│   └── index.js (export all components)
├── pages/
│   ├── HomePage.js
│   ├── BotPage.js
│   └── SettingsPage.js
├── hooks/
│   ├── useAuth.js
│   ├── useApi.js
│   └── useWebSocket.js
├── utils/
│   ├── api.js
│   ├── validators.js
│   ├── constants.js
│   └── helpers.js
├── styles/
│   ├── variables.css
│   ├── global.css
│   └── theme.css
└── App.js
```

### Commenting & Documentation

```javascript
// ✅ GOOD: Document complex logic
/**
 * Calculate weighted average price for the trading position
 * @param {Array} prices - Array of price points with volume
 * @param {number} totalVolume - Total trading volume
 * @returns {number} Weighted average price (VWAP)
 */
function calculateVWAP(prices, totalVolume) {
  // Implement VWAP calculation
}

// ✅ GOOD: Explain the WHY, not the WHAT
function delay(ms) {
  // Wait before retrying to avoid overwhelming the API with requests
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ❌ BAD: Obvious comments
const name = user.name; // Get the user's name
count++; // Increment count
```

---

## API & Data Handling Best Practices

### API Calls

```javascript
// ✅ GOOD: Centralized API client
const api = {
  users: {
    get: (id) => fetch(`/api/users/${id}`),
    create: (data) => fetch(`/api/users`, { method: 'POST', body: JSON.stringify(data) }),
    delete: (id) => fetch(`/api/users/${id}`, { method: 'DELETE' })
  }
};

// ✅ GOOD: Error handling with user feedback
async function loadUser(userId) {
  try {
    const response = await fetch(`/api/users/${userId}`);
    if (response.status === 404) throw new Error('User not found');
    if (!response.ok) throw new Error('Failed to load user');
    return await response.json();
  } catch (error) {
    showUserNotification(`Error: ${error.message}`);
    throw error;
  }
}

// ✅ GOOD: Loading and error states
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
```

### Validation

```javascript
// ✅ GOOD: Input validation
function validateEmail(email) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

// ✅ GOOD: Schema validation for API responses
const userSchema = {
  id: 'number',
  name: 'string',
  email: 'string'
};

function validateUser(data) {
  for (const [key, type] of Object.entries(userSchema)) {
    if (typeof data[key] !== type) {
      throw new Error(`Invalid ${key}: expected ${type}`);
    }
  }
}
```

---

## Performance Best Practices

### Bundle Size

- **Keep main bundle under 100KB** gzipped
- Use code splitting for routes
- Remove unused dependencies
- Lazy-load components
- Use tree-shaking in build

### Rendering Performance

- Memoize expensive components
- Use useCallback for functions passed to children
- Use useMemo for expensive calculations
- Avoid inline functions in props
- Avoid inline objects in props
- Use keys correctly in lists

### Network Performance

- Batch API requests where possible
- Use pagination for large datasets
- Compress responses (gzip)
- Cache when appropriate
- Use WebSocket for real-time instead of polling
- Debounce/throttle frequent updates

---

## Security Best Practices

### Authentication & Tokens

```javascript
// ✅ GOOD: Store token securely
const setAuthToken = (token) => {
  // Store in httpOnly cookie (more secure than localStorage)
  // Or in memory + use refresh token pattern
  localStorage.setItem('refreshToken', token);
};

// ❌ BAD: Store sensitive tokens in localStorage
const token = localStorage.getItem('authToken');
```

### XSS Prevention

```javascript
// ✅ GOOD: React escapes by default
function Post({ content }) {
  return <div>{content}</div>; // Content is automatically escaped
}

// ❌ BAD: dangerouslySetInnerHTML
function Post({ content }) {
  return <div dangerouslySetInnerHTML={{ __html: content }} />;
}

// ✅ GOOD: Sanitize if you must use HTML
import DOMPurify from 'dompurify';
function Post({ content }) {
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }} />;
}
```

### Input Validation

```javascript
// ✅ GOOD: Always validate user input
function handleSubmit(formData) {
  if (!validateFormData(formData)) {
    showError('Invalid form data');
    return;
  }
  submitForm(formData);
}

// ❌ BAD: Trust user input
function handleSubmit(formData) {
  submitForm(formData); // Could contain malicious data
}
```

---

## Testing Best Practices

### Component Tests

```javascript
// ✅ GOOD: Test behavior, not implementation
test('Button calls onClick when clicked', () => {
  const handleClick = jest.fn();
  const { getByRole } = render(<Button onClick={handleClick}>Click me</Button>);
  fireEvent.click(getByRole('button'));
  expect(handleClick).toHaveBeenCalled();
});

// ❌ BAD: Test implementation details
test('Button sets state when clicked', () => {
  const wrapper = shallow(<Button />);
  wrapper.find('button').simulate('click');
  expect(wrapper.state().clicked).toBe(true);
});
```

### Mock Data

```javascript
// ✅ GOOD: Use realistic mock data
const mockUser = {
  id: 1,
  name: 'John Doe',
  email: 'john@example.com',
  createdAt: '2024-01-01'
};

// ❌ BAD: Use unrealistic data
const mockUser = { a: 1, b: 2 };
```

---

## Accessibility Best Practices

### Semantic HTML

```javascript
// ✅ GOOD: Use semantic elements
function Navigation() {
  return (
    <nav>
      <ul>
        <li><a href="/home">Home</a></li>
        <li><a href="/about">About</a></li>
      </ul>
    </nav>
  );
}

// ❌ BAD: Use divs for everything
function Navigation() {
  return (
    <div>
      <div>
        <div onClick={() => goto('/home')}>Home</div>
        <div onClick={() => goto('/about')}>About</div>
      </div>
    </div>
  );
}
```

### ARIA Labels

```javascript
// ✅ GOOD: Provide ARIA labels
<button aria-label="Close menu">✕</button>

// ✅ GOOD: Use semantic form elements
<label htmlFor="email">Email:</label>
<input id="email" type="email" />

// ❌ BAD: No labels or ARIA
<button>✕</button>
<input />
```

---

## Quick Reference Checklist

Before committing code, verify:

- [ ] No `var` declarations (use const/let)
- [ ] All async functions have try/catch
- [ ] Props are documented (PropTypes or TypeScript)
- [ ] Components under 300 lines
- [ ] No inline functions in props
- [ ] useEffect has correct dependencies
- [ ] All API errors handled
- [ ] No console.log in production code
- [ ] No hardcoded secrets or API keys
- [ ] Component has tests
- [ ] WCAG accessibility checked
- [ ] No unused imports or variables
- [ ] Error handling for async operations
- [ ] Loading states shown to user
- [ ] Success/error feedback provided

---

## Additional Resources

- [React Official Docs](https://react.dev)
- [JavaScript MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [WCAG Guidelines](https://www.w3.org/WAI/standards-guidelines/wcag/)
- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
