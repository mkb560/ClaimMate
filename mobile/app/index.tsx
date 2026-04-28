import { Redirect } from 'expo-router';
import { Loading } from '@/components/Loading';
import { useAuth } from '@/auth/AuthContext';

export default function Index() {
  const { token, booting } = useAuth();
  if (booting) return <Loading />;
  return <Redirect href={token ? '/cases' : '/auth/login'} />;
}
