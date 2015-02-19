using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.Serialization.Formatters.Binary;
using System.IO;

namespace MilitaryPlanner.Helpers
{
    public class Utilities
    {
        public static T DeepClone<T>(T obj)
        {
            using (var ms = new MemoryStream())
            {
                var formatter = new BinaryFormatter();
                formatter.Serialize(ms, obj);
                ms.Position = 0;

                return (T)formatter.Deserialize(ms);
            }
        }

        public static object CloneObject(object obj)
        {
            if (obj == null) return null;

            Type ObjType = obj.GetType();

            System.Reflection.MethodInfo inst = ObjType.GetMethod("MemberwiseClone", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);

            if (inst != null)
            {
                return inst.Invoke(obj, null);
            }
            else
            {
                return null;
            }
        }
    }
}
